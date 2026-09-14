## Context

The repo boots one checkout at `https://clients.localhost` via `dev.sh` (tmux + `portless <basename>` + `runserver`). Verified current state: `dev.sh` derives session/domain from `basename $PWD` and scans ports from 8000 (concurrent-safe naming); `venv/` and `.env*` are gitignored so worktrees start empty; `.env.dev` hardcodes the single `clients.localhost` domain; settings read hosts/URLs only from env with no `PORTLESS_URL` awareness; `docs/` is gitignored (`/docs`) so no runbook can be tracked without an exception; openspec skills under `.opencode/`, `.claude/`, `.agent/` are gitignored via `.*/`; only `openspec/changes/archive/` is tracked. Reference pattern: `vetoxzyn` (`docs/astro-worktrees.md`) — manual sibling worktrees, `portless run` auto-domains, fresh deps per sibling, `.env` copy is harmless via a `PORTLESS_URL → SITE_URL → prod` chain, agents never autostart servers. Stakeholder decisions already taken: shared Postgres kept, runbook lives in `docs/` + `AGENTS.md`, venv approach delegated (fresh venv chosen).

## Goals / Non-Goals

**Goals:**
- Any sibling worktree (`../clients-<branch>`) bootstraps to a running dev server at its own accurate portless domain with one script plus `./dev.sh`.
- Concurrent worktrees never fight over ports, domains, tmux sessions, venvs, or openspec proposals.
- `.env` copies are harmless across siblings (URL/host resolution derives per checkout).
- AI agent can create a fully ready worktree with a single tracked command in the same session.

**Non-Goals:**
- Per-worktree Postgres databases (user chose shared `clients` DB; sqlite escape hatch documented only).
- Switching `dev.sh` to `portless run` branch-subdomain URLs (keeps current basename-domain model; smaller diff).
- Production deploy changes (Coolify/Docker path untouched).
- The `worktree_create`/`worktree_delete` plugin tools (vetoxzyn rule: manual siblings in the same session; the script reproduces that semantics).

## Decisions

- **Keep `portless <basename>` domain model, honor injected `$PORT`.** Alternative was switching to `portless run` (`https://<branch>.clients.localhost`). Rejected: current basename model (`https://clients-<branch>.localhost`) is already concurrent-safe and needs no proxy-behavior verification inside tmux; the actual collision risk is ports, not names. `dev.sh` will prefer portless-injected `$PORT` when set (fail fast if taken, mirroring astro `strictPort`), keeping the `ss` scan only as fallback for direct runs.
- **Settings URL chain `PORTLESS_URL → HOST → prod fallback` + `.localhost` host allowance.** Alternative was patching `.env.dev` hosts per worktree in the bootstrap script. Rejected as fragile bookkeeping: with the chain, a copied `.env.dev` resolves each checkout's own domain automatically (same harmless-copy design as vetoxzyn's `PORTLESS_URL → SITE_URL → prod`). `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` accept `.localhost` subdomains in dev.
- **Tracked `worktree-new.sh` in the same session instead of plugin tools.** Alternative was `worktree_create`/`worktree_delete`. Rejected per the vetoxzyn rule quoted in the reference doc (new terminal, central-store nesting); the script performs the same sibling lifecycle (`add → venv → pip install → env copy → migrate → openspec skill sync`) where the agent already is.
- **Narrow gitignore exception `!docs/django-worktrees.md` instead of untracking `/docs`.** Alternative was moving the runbook to repo root. Rejected: user asked for `docs/`; the exception keeps the rest of `/docs` ignored while the runbook (plus `.env.example`, which is tracked) carries into worktrees.
- **Fresh `venv` per worktree, never symlinked.** Mirrors vetoxzyn's no-symlink rule (package managers abort or pollute across checkouts). Cost is one `pip install` per sibling; correctness wins.
- **Openspec isolation: `archive/`-only sharing + `.opencode` markdown hand-sync.** Active `changes/*` stay per-worktree (already gitignored); the script syncs `skills/openspec-*` + `commands/opsx-*.md` markdown so the agent's openspec workflow functions in siblings.
- **Finish via `worktree-done.sh`: true merge (`--no-ff`), never squash, never auto-resolve.** Alternative was squash-on-merge (vetoxzyn team rule). Rejected: the goal is keeping all changes from both sides with full history. On conflict the script stops, lists conflicted files, and leaves the tree conflicted for the user — the agent asks how to proceed instead of resolving unilaterally. Cleanup (stop server, remove, prune, `branch -d`) runs only after a correct merge; `-d` (not `-D`) refuses unmerged work as a last guard. A re-run resumes an in-progress merge (completes the commit, then cleans up).

## Risks / Trade-offs

- [Shared Postgres across concurrent worktrees] → migrations/data clash possible; mitigation: runbook documents the one-line `DB_ENGINE=django.db.backends.sqlite3` escape hatch, tests already force sqlite.
- [Merged migrations from both sides] → two branches adding migrations can merge cleanly in git but conflict in Django's migration graph; mitigation: `worktree-done.sh` runs `migrate` after merging and reports failures instead of cleaning up, so the agent fixes the graph before the branch disappears.
- [`dev.sh` re-attach semantics per basename] → two checkouts with the same dir basename collide on tmux session; mitigation: sibling naming convention `clients-<branch>` makes basenames unique; runbook states it.
- [Branch names with `/`] → portless sanitizes subdomains/dots; mitigation: runbook requires `portless list` check after first boot.
- [Agents autostarting servers under `OPENCODE_*` env] → orphaned proxy routes (vetoxzyn § "Running under AI agents"); mitigation: agents never autostart; runbook documents foreground `./dev.sh` + `portless list` verification.
- [Safari/Firefox `.localhost` resolution] → mitigation: runbook documents `portless hosts sync`.
