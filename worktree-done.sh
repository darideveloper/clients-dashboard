#!/bin/bash
# Merge a sibling worktree branch into the current branch (keeping both sides),
# then fully clean up the sibling. Conflicts stop the script for the user.
# Usage: ./worktree-done.sh <sibling-dir> [into-branch]
set -e

MAIN=$(cd "$(dirname "$0")" && pwd)
cd "$MAIN"
DIR=$1
INTO=${2:-$(git branch --show-current)}

if [ -z "$DIR" ]; then
    echo "Usage: $0 <sibling-dir> [into-branch]"
    exit 1
fi
DIR_ABS=$(cd "$DIR" 2>/dev/null && pwd) || { echo "Not a directory: $DIR"; exit 1; }
if [ "$DIR_ABS" = "$MAIN" ]; then
    echo "Refusing to finish the main checkout itself."
    exit 1
fi
BRANCH=$(git -C "$DIR_ABS" branch --show-current 2>/dev/null) || BRANCH=""
if [ -z "$BRANCH" ]; then
    echo "Sibling is on a detached HEAD; create a branch there first."
    exit 1
fi
if [ "$BRANCH" = "$INTO" ]; then
    echo "Sibling branch ($BRANCH) is the target branch; nothing to merge."
    exit 1
fi

# 1. Openspec archive sync (active proposals are gitignored and don't transfer)
if [ -d "$DIR_ABS/openspec/changes/archive" ]; then
    mkdir -p "$MAIN/openspec/changes/archive"
    cp -rn "$DIR_ABS"/openspec/changes/archive/. "$MAIN/openspec/changes/archive/" 2>/dev/null || true
fi

# 2. Pre-flight: sibling fully committed (everything must travel via the
# branch); main tracked-clean (untracked files can't be affected by a merge)
if [ -n "$(git -C "$DIR_ABS" status --porcelain)" ]; then
    echo "Sibling has uncommitted changes; commit or stash there first."
    exit 1
fi
RESUME=""
if git -C "$MAIN" rev-parse --verify --quiet MERGE_HEAD >/dev/null; then
    RESUME=1
elif ! git -C "$MAIN" diff --quiet || ! git -C "$MAIN" diff --cached --quiet; then
    echo "Main checkout has uncommitted tracked changes; commit or stash first."
    exit 1
fi

# 3. Merge keeping both sides (re-runs resume an in-progress merge)
if [ -z "$RESUME" ]; then
    git -C "$MAIN" checkout --quiet "$INTO"
    if ! git -C "$MAIN" merge --no-ff --no-edit "$BRANCH"; then
        echo "Merge conflicts — nothing resolved, nothing cleaned up."
        echo "Conflicted files:"
        git -C "$MAIN" diff --name-only --diff-filter=U | sed 's/^/  /'
        echo "Resolve them, then re-run: $0 $DIR $INTO"
        exit 1
    fi
else
    if [ -n "$(git -C "$MAIN" diff --name-only --diff-filter=U)" ]; then
        echo "Merge still conflicted — nothing cleaned up. Conflicted files:"
        git -C "$MAIN" diff --name-only --diff-filter=U | sed 's/^/  /'
        echo "Resolve them, then re-run: $0 $DIR $INTO"
        exit 1
    fi
    git -C "$MAIN" commit --no-edit --quiet
fi

# 4. Migrate merged tree (shared Postgres; both sides may add migrations)
VENV="venv"
[ -d ".venv" ] && VENV=".venv"
if ! $VENV/bin/python manage.py migrate --noinput; then
    echo "Migration failed after merge; branch and worktree kept for inspection."
    exit 1
fi

# 5. Full cleanup (branch -d refuses unmerged work as a last guard)
NAME=$(basename "$DIR_ABS")
tmux kill-session -t "${NAME}_dev" 2>/dev/null || true
if ! git -C "$MAIN" worktree remove "$DIR_ABS"; then
    echo "Could not remove worktree (a live server may hold it); stop it and re-run."
    exit 1
fi
git -C "$MAIN" worktree prune
git -C "$MAIN" branch -d "$BRANCH"
echo "Merged $BRANCH into $INTO and removed $DIR."
