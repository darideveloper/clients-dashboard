## 1. Settings URL/host chain

- [x] 1.1 Resolve public dev URL as `PORTLESS_URL` → `HOST` → prod fallback in `project/settings.py`
- [x] 1.2 Accept `.localhost` subdomain requests (hosts, CORS, CSRF) in dev
- [x] 1.3 Verify `python manage.py check` green and sibling-origin scenario passes

## 2. dev.sh injected-port support

- [x] 2.1 Prefer portless-injected `$PORT` when set and free, keep `ss` scan as fallback
- [x] 2.2 Verify two concurrent siblings get distinct ports and both routes appear in `portless list`

## 3. Tracked bootstrap inputs

- [x] 3.1 Add `.gitignore` exceptions `!.env.example` and `!docs/django-worktrees.md`
- [x] 3.2 Add tracked `.env.example` (dev URL placeholder, no secrets)
- [x] 3.3 Verify `git check-ignore docs/django-worktrees.md .env.example` reports neither ignored

## 4. worktree-new.sh bootstrap script

- [x] 4.1 Implement `worktree-new.sh <dir> [branch]`: worktree add, fresh venv, pip install, env copy, migrate, `.opencode` skills/commands sync
- [x] 4.2 Verify one trial sibling bootstraps from scratch and `./dev.sh` serves its basename domain

## 5. Docs and conventions

- [x] 5.1 Write `docs/django-worktrees.md` (layout, lifecycle, bootstrap, stopping, troubleshooting, archive-only openspec rule)
- [x] 5.2 Add `AGENTS.md` § Git worktrees (lifecycle, bootstrap, gotchas, sqlite escape hatch)
- [x] 5.3 Full verification: two concurrent siblings serving, `portless list` truth, stop-then-remove clean

## 6. Careful merge finish

- [x] 6.1 Amend proposal/design/specs with the merge-finish requirement
- [x] 6.2 Implement `worktree-done.sh`: merge sibling branch keeping both sides, stop-and-ask on conflict, full cleanup only after correct merge
- [x] 6.3 Document the Finish flow in `docs/django-worktrees.md` + `AGENTS.md` merge line
- [x] 6.4 Add `.fuse_hidden*` to `.gitignore`
- [x] 6.5 Live trial: clean merge on throwaway branches + full cleanup
- [x] 6.6 Live trial: conflicting merge stops cleanly with conflict list, no cleanup
