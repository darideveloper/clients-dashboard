#!/bin/bash
# Bootstrap a sibling git worktree ready to run: venv, deps, env, migrate,
# openspec skills. Usage: ./worktree-new.sh ../clients-<branch> [branch] [base]
set -e

MAIN=$(cd "$(dirname "$0")" && pwd)
DIR=$1
BRANCH=$2
BASE=$3

if [ -z "$DIR" ]; then
    echo "Usage: $0 <sibling-dir> [branch] [base]"
    exit 1
fi

if [ -n "$(git -C "$MAIN" status --porcelain)" ]; then
    echo "Warning: $MAIN has uncommitted changes; the sibling starts from HEAD without them."
fi

# 1. Worktree (sibling layout, never nested)
if [ -n "$BRANCH" ]; then
    if git -C "$MAIN" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
        git -C "$MAIN" worktree add "$DIR" "$BRANCH"
    else
        git -C "$MAIN" worktree add "$DIR" -b "$BRANCH" "${BASE:-HEAD}"
    fi
else
    git -C "$MAIN" worktree add "$DIR"
fi

cd "$DIR"

# 2. Fresh venv + deps per sibling (never symlinked)
[ -d "venv" ] || python3 -m venv venv
venv/bin/pip install -r requirements.txt

# 3. Env: copy from main checkout, else template (copied HOST is harmless:
# settings resolve PORTLESS_URL first, then HOST)
[ -f ".env" ] || { [ -f "$MAIN/.env" ] && cp "$MAIN/.env" .env || echo "ENV=dev" > .env; }
[ -f ".env.dev" ] || { [ -f "$MAIN/.env.dev" ] && cp "$MAIN/.env.dev" .env.dev || cp .env.example .env.dev; }

# 4. Migrate (shared Postgres per project decision; tests always use sqlite)
venv/bin/python manage.py migrate --noinput

# 5. Openspec skills/commands sync (markdown only; active proposals stay isolated)
if [ -d "$MAIN/.opencode" ]; then
    mkdir -p .opencode/skills .opencode/commands
    cp -rn "$MAIN"/.opencode/skills/openspec-* .opencode/skills/ 2>/dev/null || true
    cp -rn "$MAIN"/.opencode/commands/opsx-*.md .opencode/commands/ 2>/dev/null || true
fi

NAME=$(basename "$PWD")
echo "Ready: $DIR (branch: $(git branch --show-current))"
echo "Next: cd $DIR && ./dev.sh   # -> https://$NAME.localhost (verify with: portless list)"
