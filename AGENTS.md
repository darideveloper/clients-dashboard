# AGENTS.md

<!-- ponytail -->
Always load the ponytail skill at session start (call skill({ name: "ponytail" })). Enforce minimal/YAGNI solutions by default.
<!-- ponytail -->

## Admin Excel Export Convention

- New admin-registered models **must** inherit `project.admin_base.ModelAdminUnfoldBase` to automatically get the bulk actions **Export to Excel** and **Export to Excel (with related)** (gated on `view`, with `select_related`/`.iterator()`, RFC 5987 filenames).
- New `ourlives` models must inherit `project.admin_base.OurlivesModelAdminBase` (or `SingletonModelAdmin` + `OurlivesExportMixin` + `ModelAdminUnfoldBase` for singletons like `AppSettings`) to also expose the header button **Export all app data** (Unfold `actions_list`/`actions_detail` via `OurlivesExportMixin`, permission `has_module_perms("ourlives")`). `build_full_app_workbook()` discovers `ourlives` models deterministically via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` so no per-model wiring is needed.
- Keep all admin bases/mixins in single source `project/admin_base.py` — do not create `ourlives/admin_base.py`.

## Git Worktrees

One checkout per branch, all runnable at once (`main` → `https://clients.localhost`,
sibling `../clients-<branch>` → `https://clients-<branch>.localhost`).
Full runbook: `docs/django-worktrees.md`.

- Manual siblings only, same session. Never `worktree_create` / `worktree_delete`
  plugin tools; never nest a worktree inside the main checkout.
- Lifecycle: `git status` clean first, then `./worktree-new.sh ../clients-<branch> [branch] [base]`,
  `cd` in, `./dev.sh`. Stop the dev server before `git worktree remove`; `prune` after.
- Finish: `./worktree-done.sh ../clients-<branch> [into]` merges keeping both sides
  (`--no-ff`), stops + asks on any conflict (never auto-resolve), then full cleanup
  (stop server, remove, prune, `branch -d`). Sibling must be fully committed clean,
  main tracked-clean first.
- Bootstrap per sibling is fresh `venv` + `pip install` (never symlink), `.env` copy
  (harmless — settings resolve `PORTLESS_URL → HOST`), `migrate`, openspec skills sync.
- Gotchas: shared Postgres `clients` DB (migrate from one sibling at a time;
  `DB_ENGINE=django.db.backends.sqlite3` escape hatch); openspec active proposals stay
  isolated (only `archive/` shared back); agents never autostart servers
  (verify with `portless list`).

## Context7

Always use the Context7 MCP server when you need library/API documentation, code generation, setup or configuration steps without you having to explicitly ask. Use the `resolve-library-id` and `query-docs` MCP tools to fetch current documentation.
