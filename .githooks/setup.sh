#!/bin/bash
#
# Setup script for git hooks
# Run this once after cloning the repo
#

set -e

SCRIPT_DIR=$(dirname "$0")
REPO_ROOT=$(git rev-parse --show-toplevel)

echo "🔧 Setting up git hooks..."

# Configure git to use custom hooks directory
git config core.hooksPath .githooks

# Make hooks executable
chmod +x "$SCRIPT_DIR/pre-commit"
chmod +x "$SCRIPT_DIR/commit-msg"

echo "✅ Git hooks configured!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: ruff format, ruff lint, pytest"
echo "  - commit-msg: conventional commit validation"
echo ""
echo "To skip hooks temporarily, use: git commit --no-verify"
