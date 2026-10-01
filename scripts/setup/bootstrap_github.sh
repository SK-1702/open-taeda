#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <github-remote-url>"
  exit 2
fi

REMOTE="$1"
git init
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"
git add .
git commit -m "initial Open TAEDA v0.1 platform"
git push -u origin main
