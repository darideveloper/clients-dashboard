## Context

`ourlives/ingestion.py:ingest()` currently turns each non-empty `code-1..code-20` into a live `InvitationCode` (`max_use=1`, `is_active=True`, `project=ourlens`, `code_type` from bundle label) and accumulates `Order.tokens_used`. `InvitationCode.code` is globally unique, so placeholder literals (e.g. `OL-88`'s five identical `P03TST-`) collide and are skipped with warnings. Every row inflates `AppSettings.tokens_assigned` and appears as a usable code in admin, usage stats, and Excel. Raw payloads are already preserved in `FormWebhookEvent.payload`, but are not searchable or exportable. Per explore-phase decisions: per-code search is required, bundle label stays filterable, reposts replace, Excel gets its own sheet, existing codes stay untouched, generation path is removed (not flagged), `tokens_used` stays `0` for new orders.

## Goals / Non-Goals

**Goals:**
- Store every non-empty `code-N` verbatim per order, searchable by value and bundle in admin.
- Keep full-app Excel export covering the new rows (one row per code) with zero per-model wiring.
- Honest counts with no sync machinery: freeze the legacy `tokens_used` writer and display the live count from the existing annotation.
- Replace-on-repost so stored codes always mirror the latest form submission.
- Manual CRUD on `InvitationCode`s keeps working with zero changes.

**Non-Goals:**
- No migration or deletion of existing `InvitationCode` rows.
- No per-code usage tracking (`current_use`/`max_use`), activation, or pool validation on requested codes.
- No signals, backfill migration, or sync helpers — the live count comes from the existing queryset annotation, which cannot drift by construction.
- No feature flag / dual-write; generation is removed from the ingestion path outright.
- No changes to pilot `OrderItem`, org/rep/contact/address, pool/usage calculations, bulk import, or audit logic.

## Decisions

- **New `OrderRequestedCode` model (not JSONField on `Order`)** — per-code search/filter and one-row-per-code Excel sheet require real rows. Alternatives: JSONField (rejected — not queryable, export would need custom concatenation); inactive `InvitationCode`s (rejected — abuses `unique=True`, pollutes pool stats and usage %).
  - Fields: `order FK CASCADE related_name="requested_codes"`, `sequence PositiveInteger 1..20`, `value CharField(50)`, `code_type FK PROTECT nullable` (resolved from `how-many-additional-codes-do-you-require`, null when blank). No `unique` on `value` — identical literals across orders are legal. `Meta.ordering = ["order", "sequence"]`.
- **Bundle request on `Order`** — `requested_codes_wanted Boolean default False` (from `i-would-like-additional-codes`), `requested_codes_bundle CharField blank` (verbatim label) + `requested_code_type FK PROTECT nullable` (resolved `CodeType`). Lets staff filter "asked for 20 but typed 3" without joining codes. Alternative (bundle only on code rows) rejected — order-level filter needs order-level columns.
- **Replace-on-repost** — on reconcile, inside `transaction.atomic`, `order.requested_codes.all().delete()` then bulk-insert current non-empty slots (including within-order duplicate literals, one row per slot). Rationale: requested strings carry no `current_use` history to preserve, unlike live codes. Idempotent: same payload → same rows.
- **Remove `_create_codes()` from `ingest()`** — delete the call and `tokens_used` accumulation; leave no flag. Alternative (settings flag) rejected per decision to rebuild later from `OrderRequestedCode` when client re-enables.
- **`tokens_used` frozen, live count via row-count annotation** — `Order.tokens_used` stops being written (legacy values kept, new webhook orders read `0`); the Order admin shows the live code count from a `_live_codes_count=Count("invitation_codes", distinct=True)` annotation added in `OrderAdmin.get_queryset()` (readonly display, `ordering="_live_codes_count"`, `0` for codeless orders, `—` only for unsaved). The pre-existing `_codes_used` (`SUM(current_use)`) was rejected for this — it reads `0` for freshly created codes. Alternatives: signals + backfill + override rules (rejected — a sync subsystem to maintain a redundant counter); `@property` (rejected — loses changelist sorting); hiding the column (rejected — staff chose the live count display).
- **Manual CRUD needs no changes** — `InvitationCodeAdmin` already allows full create/link/edit; pool (`tokens_assigned/used/available`) and usage % already read live `InvitationCode` sums, so manually added codes are counted correctly with zero code changes.
- **Admin inherits `OurlivesModelAdminBase`** — new `OrderRequestedCodeAdmin` gets bulk Excel actions + full-app export sheet automatically via `build_full_app_workbook()` discovery; `TabularInline` on `OrderAdmin` (readonly sequence/value display). No changes to `project/admin_base.py`.
- **Docs + tests flip** — `ourlives/docs/form-webhook.md` codes section rewritten (requested vs. live); `test_webhook_samples.py` / `test_form_webhook.py` assert 0 invitation codes, N requested codes, gap `14→16` preserved, repost replace, `tokens_used==0`.

## Risks / Trade-offs

- [Risk] Duplicate `value` literals across orders now allowed → later promotion to `InvitationCode` (global unique) will collide → Mitigation: backfill script must dedupe/remap at promotion time; document this in design, not code.
- [Risk] Full-app export sheet order shifts (deterministic `sorted(model_name)` discovery) → Mitigation: snapshots compare by sheet name, not index.
- [Risk] Bulk delete+insert on repost briefly empties codes → Mitigation: the replace block runs inside `transaction.atomic`.
- [Risk] Staff retyping placeholder literals verbatim as real codes hits the global `unique` constraint → Mitigation: manual-workflow note in `form-webhook.md` (generate real codes, don't reuse duplicate placeholders verbatim).
- [Trade-off] One extra table + admin vs. zero-model payload-only reads — accepted because searchability was an explicit requirement.
