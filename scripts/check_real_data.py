"""Pre-commit guard: block staged lines that contain real report values.

The repo is public, so tests, docs and docstrings must use made-up numbers.
Real values only live in untracked local files (config/settings.yaml, output/,
tests/golden/report_*.json), so collect them there and fail when a staged
added line repeats one. Worktrees also read the main checkout's files.
"""

from __future__ import annotations

import codecs
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# A number not glued to a word, version string or longer number; "_" may split
# digits on either side of the point (Python literals: 123_456, 134.5_6).
NUMBER = re.compile(r'(?<![\w.])\d+(?:_\d+)*(?:\.\d+(?:_\d+)*)?(?![\w]|\.\d)')
# Thousands separators (1,234,567). Scanned separately so a tight list such as
# [134.56,0] still yields 134.56 from NUMBER.
GROUPED = re.compile(r'(?<![\w.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w]|[.,]\d)')


def is_number(text: str) -> bool:
    return bool(NUMBER.fullmatch(text) or GROUPED.fullmatch(text))


def number_tokens(line: str) -> list[str]:
    return NUMBER.findall(line) + GROUPED.findall(line)


HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)')
SOURCE_GLOBS = ('config/settings.yaml', 'output/**/*.json', 'output/**/*.csv', 'tests/golden/report_*.json')


def normalize(token: str) -> str:
    """'72.50' -> '72.5', '123_456' / '123,456' -> '123456'."""
    token = token.replace('_', '').replace(',', '')
    if '.' in token:
        token = token.rstrip('0').rstrip('.')
    return token


def is_distinctive(token: str) -> bool:
    """Numbers specific enough that a match is not a coincidence.

    Integers need 6+ digits (CP codes, byte counts); decimals need 4+
    significant digits (105.29 yes, 85.8 / 0.04 no).
    """
    token = normalize(token)
    if '.' not in token:
        return len(token) >= 6
    return len(token.replace('.', '').lstrip('0')) >= 4


def _walk(value, out: set[str]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, dict):
        for v in value.values():
            _walk(v, out)
    elif isinstance(value, list):
        for v in value:
            _walk(v, out)
    elif isinstance(value, int | float):
        out.add(normalize(repr(value)))
    elif isinstance(value, str):
        out.add(value.strip())


def _settings_identifiers(cfg: dict) -> set[str]:
    """CP codes, the CloudFront distribution id and 1Password references."""
    ids = set()
    for rt in (cfg.get('report_types') or {}).values():
        ids.update(str(c) for c in (rt or {}).get('cp_codes') or [])
    ids.add(str((cfg.get('cloudfront') or {}).get('distribution_id') or ''))
    op = cfg.get('onepassword') or {}
    ids.update(str(op.get(k) or '') for k in ('account', 'item'))
    return {i.strip() for i in ids if len(i.strip()) >= 6}


def values_from_file(path: Path) -> set[str]:
    """Distinctive numbers (and settings identifiers) found in one local data file."""
    text = path.read_text(encoding='utf-8', errors='ignore')
    if path.suffix == '.yaml':
        return _settings_identifiers(yaml.safe_load(text) or {})

    raw: set[str] = set()
    if path.suffix == '.json':
        _walk(json.loads(text), raw)
    else:
        for row in csv.reader(text.splitlines()):
            raw.update(cell.strip() for cell in row)
    return {normalize(v) for v in raw if is_number(v) and is_distinctive(v)}


def find_hits(added: list[tuple[str, int, str]], real: set[str]) -> list[tuple[str, int, str]]:
    """(file, line, matched value) for each added line that repeats a real value."""
    numbers = {v for v in real if is_number(v)}
    strings = real - numbers
    hits = []
    for path, lineno, line in added:
        for token in number_tokens(line):
            if normalize(token) in numbers:
                hits.append((path, lineno, token))
        for s in strings:
            if s in line:
                hits.append((path, lineno, s))
    return hits


def _unquote(path: str) -> str:
    """Undo git's C-style quoting of paths with non-ASCII or special characters."""
    if len(path) >= 2 and path[0] == path[-1] == '"':
        return codecs.escape_decode(path[1:-1].encode('utf-8'))[0].decode('utf-8', 'replace')
    return path


def parse_added_lines(diff: str) -> list[tuple[str, int, str]]:
    """Added lines from `git diff -U0` output as (file, line number, text).

    File headers only count before a file's first hunk, so an added line whose
    text starts with "++ " is still scanned as content.
    """
    added, path, lineno, in_hunk = [], '?', 0, False
    for line in diff.splitlines():
        if line.startswith('diff --git '):
            path, in_hunk = '?', False
        elif not in_hunk and line.startswith('+++ '):
            target = _unquote(line[4:])
            path = target[2:] if target.startswith('b/') else target
        elif m := HUNK.match(line):
            lineno, in_hunk = int(m.group(1)), True
        elif in_hunk and line.startswith('+'):
            added.append((path, lineno, line[1:]))
            lineno += 1
    return added


def _git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def _data_roots() -> list[Path]:
    top = Path(_git('rev-parse', '--show-toplevel').strip())
    main = Path(_git('rev-parse', '--path-format=absolute', '--git-common-dir').strip()).parent
    return [top] if main == top else [top, main]


def collect_real_values() -> set[str]:
    tracked = set(_git('ls-files').splitlines())
    real: set[str] = set()
    for root in _data_roots():
        for pattern in SOURCE_GLOBS:
            for path in root.glob(pattern):
                if path.relative_to(root).as_posix() in tracked or not path.is_file():
                    continue
                try:
                    real |= values_from_file(path)
                except (ValueError, yaml.YAMLError):
                    continue
    return real


def main(argv: list[str]) -> int:
    real = collect_real_values()
    if not real:
        return 0
    if argv[:1] == ['--commit-msg']:
        # commit-msg stage: pre-commit passes the message file path.
        lines = Path(argv[1]).read_text(encoding='utf-8').splitlines()
        added = [('commit message', i, line) for i, line in enumerate(lines, 1) if not line.startswith('#')]
    else:
        added = parse_added_lines(_git('diff', '--cached', '-U0', '--no-color', '--', *argv))
    hits = find_hits(added, real)
    for path, lineno, value in hits:
        print(f'{path}:{lineno}: {value!r} matches a real value from local reports/config')
    if hits:
        print('This repo is public: replace real traffic numbers / CP codes with made-up values.')
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
