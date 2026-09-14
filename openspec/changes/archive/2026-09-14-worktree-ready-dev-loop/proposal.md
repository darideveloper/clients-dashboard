## Why

Parallel feature work currently forces stash/checkout cycles in a single checkout: only one branch and one dev server can run at a time. Git worktrees plus portless give every branch its own directory and its own `.localhost` URL, but this repo is not worktree-ready — fresh worktrees miss gitignored runtime files (`venv/`, `.env*`), hardcode a single portless domain (`clients.localhost`), and have no runbook or bootstrap automation, so a new worktree does not run.

## What Changes

- Add a tracked worktree runbook (`docs/django-worktrees.md`, via a narrow `.gitignore` exception) covering layout, lifecycle, bootstrap, stopping, and troubleshooting.
- Add a tracked one-command bootstrap script (`worktree-new.sh`): `git worktree add` + fresh `venv` + `pip install -r requirements.txt` + `.env`/`.env.dev` copy + migrate, runnable by the AI agent in the same session.
- Add a tracked finish script (`worktree-done.sh`): careful merge of the sibling branch into the current branch keeping both sides, stop-and-ask on conflicts, then full cleanup (stop server, remove worktree, prune, delete branch).
- Make `dev.sh` honor portless-injected `$PORT` (fail fast when taken), keeping the current `ss` port scan only as fallback, so concurrent worktrees never fight over ports.
- Make settings resolve the public dev URL as `PORTLESS_URL → HOST → prod fallback` and accept `.localhost` hosts, so a copied `.env.dev` is harmless in any sibling and each checkout serves its own accurate portless domain.
- Add a tracked `.env.example` so a worktree can bootstrap env without the main checkout present.
- Document the `.opencode` skills/commands hand-sync and the openspec `archive/`-only rule per worktree.
- Document the worktree convention in `AGENTS.md` (layout, lifecycle, bootstrap, gotchas).

## Capabilities

### New Capabilities

- `worktree-dev-loop`: parallel git worktrees, each fully bootstrapped (venv, deps, env, migrate, openspec skills) and serving its own accurate portless domain via `./dev.sh`, runnable concurrently.

### Modified Capabilities

- `local-dev-loop`: `dev.sh` port handling changes (injected `$PORT` first, `ss` scan fallback); settings URL/host resolution changes (`PORTLESS_URL → HOST → fallback`, `.localhost` acceptance).
- `env-driven-config`: `.env.example` introduced; `.env`/`.env.dev` copy semantics per worktree documented.
- `project-bootstrap`: repo contents gain `worktree-new.sh`, `worktree-done.sh`, `docs/django-worktrees.md`, `.env.example`; `.gitignore` gains the narrow runbook exception.

## Impact

- Affected: `dev.sh`, `project/settings.py`, `.gitignore`, `AGENTS.md`; new files `worktree-new.sh`, `worktree-done.sh`, `docs/django-worktrees.md`, `.env.example`.
- No production behavior change (prod serves via Docker/gunicorn, not portless); dev-only URL/host resolution extended.
- Shared Postgres (`DB_NAME=clients`) is kept per user decision — concurrent worktrees share data; the runbook documents the `DB_ENGINE=sqlite` escape hatch.
