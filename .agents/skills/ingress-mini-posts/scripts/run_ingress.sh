#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=$(pwd)
SCRIPT_DIR=$(dirname -- $0)
MANUFACTURER=${1:-Archon-Studio}
CAMPAIGN=${2:-DnL-Deuslair}
VISIT=${3:-https://archon-studio.com/}

echo [1/4] Processing ingress...
python3 $SCRIPT_DIR/process_ingress.py --manufacturer $MANUFACTURER --campaign $CAMPAIGN --visit $VISIT

echo [2/4] Validating...
python3 $SCRIPT_DIR/validate_posts.py

echo [3/4] Committing...
cd $REPO_DIR
git add .agents _posts assets ingress
git diff --cached --quiet && echo No changes. && exit 0
NEW=$(git diff --cached --name-only --diff-filter=A)
git commit -m Add: $NEW

echo [4/4] Pushing...
git push origin main

echo DONE.
