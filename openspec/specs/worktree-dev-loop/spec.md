# worktree-dev-loop Specification

## Purpose
Parallel git worktrees with per-sibling portless domains, one-command bootstrap, and careful merge finish.
## Requirements
### Requirement: Sibling worktree bootstrap
A sibling worktree created with `git worktree add ../clients-<branch>` SHALL become a running dev checkout after the tracked bootstrap: fresh `venv`, `pip install -r requirements.txt`, `.env` + `.env.dev` copy, `python manage.py migrate`, and `.opencode` openspec skills/commands sync. Each sibling SHALL serve its own accurate portless domain via `./dev.sh` concurrently with other checkouts.

#### Scenario: New sibling runs concurrently
- **WHEN** the bootstrap completes in `../clients-feature-x` while `main` serves `https://clients.localhost`
- **THEN** `./dev.sh` in the sibling serves `https://clients-feature-x.localhost` on a non-conflicting port and `portless list` shows both routes

#### Scenario: Gitignored paths do not transfer
- **WHEN** a sibling worktree is created
- **THEN** `venv/`, `.env`, `.env.dev`, `db.sqlite3`, and `.opencode/skills/openspec-*` are absent until the bootstrap recreates them

### Requirement: Sibling layout and lifecycle
Siblings SHALL live at `../clients-<branch>` (never nested inside the main checkout), start from committed `HEAD` only, stop their dev server before `git worktree remove`, and agents SHALL never autostart dev servers.

#### Scenario: Stop before remove
- **WHEN** a sibling is deleted
- **THEN** its tmux dev session was stopped first (Ctrl+C / `tmux kill-session`) and `git worktree remove` plus `git worktree prune` complete cleanly

### Requirement: Openspec isolation across siblings
Active proposals under `openspec/changes/*` SHALL stay isolated per sibling; only `openspec/changes/archive/` is shared. Each sibling SHALL receive the `.opencode` openspec skills and commands via markdown copy so the openspec workflow functions there.

#### Scenario: Proposals do not cross
- **WHEN** a proposal is drafted in a sibling
- **THEN** it is invisible to the main checkout until its `archive/` is copied back before merge

### Requirement: Careful merge finish with full cleanup
When work in a sibling is done, the agent SHALL merge the sibling branch into the current branch keeping all changes from both sides, SHALL stop and ask the user on any conflict or issue instead of resolving unilaterally, and only after a correct merge SHALL fully clean up (stop the sibling dev server, remove the worktree, prune, delete the branch).

#### Scenario: Clean merge and cleanup
- **WHEN** `./worktree-done.sh ../clients-feature-x` runs with no conflicts
- **THEN** the sibling branch is merged into the current branch, the sibling server is stopped, the worktree is removed, and the branch is deleted

#### Scenario: Conflict stops and asks
- **WHEN** the merge produces conflicts
- **THEN** the script stops without resolving anything, lists the conflicted files, and the agent asks the user how to proceed before any cleanup
