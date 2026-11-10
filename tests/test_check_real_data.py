import json

import pytest

from scripts.check_real_data import (
    find_hits,
    is_distinctive,
    normalize,
    parse_added_lines,
    values_from_file,
)


@pytest.mark.parametrize(
    'token, expected',
    [
        ('105.29', True),
        ('47.27', True),
        ('72.50', False),  # 72.5 after normalising: 3 significant digits
        ('85.8', False),
        ('0.04', False),
        ('2026', False),
        ('1234567', True),  # CP-code sized
        ('123456789012', True),  # byte count
        ('12345', False),
    ],
)
def test_is_distinctive(token, expected):
    assert is_distinctive(token) is expected


def test_normalize_drops_trailing_zeros():
    assert normalize('72.50') == '72.5'
    assert normalize('3.00') == '3'
    assert normalize('1000') == '1000'


def test_values_from_json_report(tmp_path):
    p = tmp_path / 'report.json'
    p.write_text(json.dumps({'traffic': {'edge': 105.29, 'offload': 55.0}, 'daily_bytes': {'10/19': 765000111222}}))
    assert values_from_file(p) == {'105.29', '765000111222'}


def test_values_from_csv(tmp_path):
    p = tmp_path / 'weekly.csv'
    p.write_text('年度,CDN 每周流量TB,edge流量\n2026,10/18 - 10/24,105.29\n', encoding='utf-8')
    assert values_from_file(p) == {'105.29'}


def test_values_from_settings_keep_ids_not_labels(tmp_path):
    p = tmp_path / 'settings.yaml'
    p.write_text(
        'browser:\n  session: "akamai"\n  state_file: "profiles/x.json"\n'
        'onepassword:\n  account: "ABCDEFGH12"\n  item: "akamai-login"\n'
        'report_types:\n  tva:\n    label: "TVA"\n    cp_codes: ["9876543", "ALL"]\n'
        'cloudfront:\n  distribution_id: "E2ABCDEF123456"\n  region: "us-east-1"\n',
        encoding='utf-8',
    )
    assert values_from_file(p) == {'9876543', 'E2ABCDEF123456', 'ABCDEFGH12', 'akamai-login'}


def test_parse_added_lines_tracks_file_and_line():
    diff = (
        'diff --git a/t.py b/t.py\n--- a/t.py\n+++ b/t.py\n'
        '@@ -10,0 +11,2 @@\n+edge = 105.29\n+ok = 1\n'
        'diff --git a/gone.py b/gone.py\n--- a/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x = 105.29\n'
    )
    assert parse_added_lines(diff) == [('t.py', 11, 'edge = 105.29'), ('t.py', 12, 'ok = 1')]


def test_parse_added_lines_quoted_path_and_plus_content():
    # git quotes non-ASCII paths; an added line "++ heading" shows as "+++ heading".
    diff = (
        'diff --git "a/\\346\\226\\207.md" "b/\\346\\226\\207.md"\n'
        '--- "a/\\346\\226\\207.md"\n+++ "b/\\346\\226\\207.md"\n'
        '@@ -0,0 +1,3 @@\n+edge 105.29\n+++ heading\n+x 105.29\n'
    )
    assert parse_added_lines(diff) == [
        ('文.md', 1, 'edge 105.29'),
        ('文.md', 2, '++ heading'),
        ('文.md', 3, 'x 105.29'),
    ]


@pytest.mark.parametrize(
    'text',
    [
        'x = 123_456_789_012',
        'bytes 123,456,789,012',
        '[134.56,0]',
        '[0,134.56]',
        'x = 134.5_6',
        '{"edge":134.56,"origin":1}',
    ],
)
def test_find_hits_grouped_digits_and_tight_lists(text):
    real = {'123456789012', '134.56'}
    assert len(find_hits([('a.py', 1, text)], real)) == 1


def test_find_hits_numbers_and_strings():
    real = {'105.29', '9876543', 'E2ABCDEF123456'}
    added = [
        ('a.py', 1, "_result('summary', {'edge': 105.290})"),
        ('a.py', 2, 'cp = "9876543"'),
        ('b.md', 3, 'dist E2ABCDEF123456 here'),
        ('c.py', 4, 'version = "1105.29.1"; x = 13.45'),
    ]
    assert find_hits(added, real) == [
        ('a.py', 1, '105.290'),
        ('a.py', 2, '9876543'),
        ('b.md', 3, 'E2ABCDEF123456'),
    ]
