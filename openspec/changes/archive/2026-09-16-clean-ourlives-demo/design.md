## Context

`seed_ourlives_demo` (`ourlives/management/commands/seed_ourlives_demo.py`, spec `demo-seed`) creates scoped demo rows: `Demo `-prefixed orgs/projects, `test-` emails for reps/contacts, with children reachable via Demo orgs. Its `_clear_demo` wipes everything at once with no preview, no choice, and no tests — fine for dev reset, unsafe as a prod cleanup story. The FK/delete graph from `ourlives/models.py` dictates removal order: `Contact.organization` / `OrganizationAddress.organization` / `OrderItem.order` CASCADE; `Order.organization|rep`, `InvitationCode.project|organization|order|code_type`, `Contact.contact_type` PROTECT (wrong order → `ProtectedError`); `Order.currency|pilot_currency`, `Organization.assigned_rep` SET_NULL (safe). `AppSettings` is a django-solo singleton with `tokens_available = total − assigned`, so deleting codes frees pool capacity without touching `total_tokens`. Docs live in `ourlives/docs/` (`demo-seed.md` + `crm-erd.md`).

## Goals / Non-Goals

**Goals:**
- Interactive per-org audit: preview table, then one prompt per `Demo` org showing every related row by natural identifier, then prompts for leftover `Demo` projects / `test-` reps.
- FK-safe deletion: per-group `transaction.atomic()`, strict reverse-FK order, handmade rows and lookups provably untouched.
- Automation modes: `--dry-run` (counts only) and `--yes` (delete all, no prompts).

**Non-Goals:**
- No model/migration/admin changes; no `total_tokens` shrinking; no prod ENV guard; no StripeEvent handling (never seeded); no per-`OrderItem`/`InvitationCode` prompts (grouped under their org).

## Decisions

- **New command `ourlives/management/commands/clean_ourlives_demo.py`, stdlib `input()`, no new dependencies.** Alternative: raw `shell` snippets — rejected, untestable and typo-prone on prod. Alternative: admin bulk action — rejected, no per-org drill-down and checkbox hunting.
- **Reuse the seed's scope querysets (`Demo ` prefix / `test-` email) via shared constants.** Rationale: scan ↔ seed ↔ clear can never drift; the audit's `_clear_demo` order is the proven deletion order. If constants move to a shared module during implementation, both commands import from it.
- **Group prompts by org, then projects, then reps.** Rationale: ~13 prompts instead of ~60 per-record prompts; org is the FK root of the whole subgraph (contacts/addresses CASCADE, orders PROTECT, codes reachable). Per-item prompts rejected as tedious and error-prone under decision fatigue.
- **Per-org detail block with natural identifiers** (contact `email — name (type)`, address `line1, city`, order `order_number — po — scans×cost — types — date`, item `product ×qty @ price = line_total`, code `code — project — use/max % — order`). Rationale: the user explicitly asked to see detailed data per related row before deciding.
- **Per-group `transaction.atomic()` (one org = one commit), not one giant transaction.** Rationale: `Ctrl-C`/quit keeps completed deletions; a single atomic would roll back 20 confirmed deletions on abort.
- **Controls `d/k/a/q/?` (`--dry-run`, `--yes`).** Rationale: user-chosen in scope review; `?` prints legend, `a` deletes all remaining without further prompts, `q` quits keeping the rest.
- **Leave `total_tokens` untouched (scope decision A).** Rationale: `tokens_available` recomputes from `assigned`, so capacity frees automatically; shrinking the singleton on prod without asking risks breaking concurrent token issuance.
- **No ENV/prod guard (scope decision).** Rationale: user explicitly wants identical local/prod behavior; safety comes from scoping + preview + per-group confirm instead.

## Risks / Trade-offs

- [Risk] `test-` rep shared by a handmade org (assigned_rep SET_NULL survives org delete, rep prompt could orphan nothing but handmade org keeps working) → Mitigation: rep prompt shows linked handmade orgs count; deleting a rep only NULLs `assigned_rep`, never deletes orgs.
- [Risk] Concurrent `InvitationCode` creation during clean changes pool counts mid-run → Mitigation: per-group atomicity; final summary recomputes counts after run.
- [Risk] Non-interactive stdin (piped/CI) hangs on `input()` → Mitigation: detect non-tty and require `--yes`/`--dry-run`, else exit with usage error.
- [Trade-off] Orphan `Demo` codes whose org was hand-deleted earlier are found via org-prefix queryset only — codes with non-Demo orgs are never touched, by design (same scope as seed).
