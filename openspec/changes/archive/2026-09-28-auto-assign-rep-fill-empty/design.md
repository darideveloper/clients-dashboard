## Context

`ingest()` (`ourlives/ingestion.py`) resolves `org` via `get_or_create_org()` and `rep` via `get_or_create_rep()`, links the rep to the `Order`, but never touches `Organization.assigned_rep` (nullable FK, `SET_NULL`). Result: every webhook-created organization lands with no rep, requiring manual assignment. This predates the requested-codes change (verified via `git log -S`).

## Goals / Non-Goals

**Goals:**
- New organizations leave ingestion with the submitting rep assigned.
- Existing unassigned organizations get assigned on the next submission touching them.
- Manual assignments are never clobbered by later submissions.

**Non-Goals:**
- No "last submitter wins" overwrite semantics (explicitly rejected per user decision).
- No backfill for organizations already in the DB with no rep and no future submissions.
- No changes to matching rules, admin, or exports.

## Decisions

- **Fill-if-empty guard in `ingest()`** — after resolving `org` + `rep`: `if org.assigned_rep_id is None: org.assigned_rep = rep; org.save(update_fields=["assigned_rep"])`. Placed right after rep resolution so it applies to both create and reconcile paths. Alternative (always overwrite) rejected — would destroy manual reassignments on every repost.
- **Check `assigned_rep_id`, not the relation** — avoids an extra query when already set; single `UPDATE` only on the transition.
- **No `update_fields` battle on repost** — the order update path (`setattr` loop + `order.save()`) is untouched; org save is independent and conditional.

## Risks / Trade-offs

- [Risk] Two reps submit for the same new org near-simultaneously → first writer wins, second sees it set → Mitigation: acceptable; manual correction remains possible in admin (same as any race on match-or-create).
- [Trade-off] Pre-existing unassigned orgs with no future submissions stay unassigned — accepted (no backfill; staff assigns once in admin).
