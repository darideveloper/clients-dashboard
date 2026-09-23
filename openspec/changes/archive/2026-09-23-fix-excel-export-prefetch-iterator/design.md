## Context

`OrderAdmin.get_queryset()` (`ourlives/admin.py:539-548`) chains `.select_related(...).prefetch_related("order_types").prefetch_related("items__product__currency")` plus `annotate_order_usage`. Admin bulk actions receive the changelist queryset, so both prefetches survive into `build_workbook_for_queryset()` → `_write_sheet_for_model()` (`utils/excel_export.py:295-338`), which calls `qs.iterator()` with no `chunk_size`. Django ≥4.1 raises `ValueError` whenever `iterator()` follows `prefetch_related` without `chunk_size` (verified against current Django docs: default 2000 applies only when no prefetch exists). Second crash site: the `include_related` fallback ID loop (`excel_export.py:383`). Existing tests only cover prefetch-free models (`InvitationCode`, `Project`), so the bug slipped through. `columns_for_model()` exports concrete fields only — M2M / reverse-FK prefetched relations (`order_types`, `items`) are never read — so the inherited prefetches are pure overhead on export.

## Goals / Non-Goals

**Goals:**
- Both Excel actions succeed on Order (and any future `prefetch_related` admin) with identical sheets/rows as before.
- Single shared-helper fix covering per-model, with-related, and full-app paths.
- Regression tests that fail before / pass after.

**Non-Goals:**
- No change to changelist querysets, list display, filters, or permissions.
- No new export columns (M2M sheets remain out of scope — forward FK/OneToOne single-hop only).
- No chunk-size configurability or streaming-format changes.

## Decisions

- **Clear + chunk (Option C): `qs.prefetch_related(None)` then `iterator(chunk_size=2000)` in `_write_sheet_for_model`, same chunk on the fallback loop.**
  - Why both: clearing removes the useless prefetch queries (export never reads M2M); explicit chunk is defense-in-depth so a future caller that re-adds a prefetch can't re-crash. `2000` matches Django's own implicit default — boring and consistent.
  - Alternatives: chunk-only (fixes crash, keeps wasteful prefetch queries per chunk); clear-only (fixes crash today, re-crashes the day someone re-adds a prefetch); fix in `OrderAdmin` (whack-a-mole — `RepAdmin` has the same latent bug); drop `iterator()` (loads full table into memory — regression for full-app export).
- **Guard with `hasattr(qs, "prefetch_related")`** so lists/mocks without queryset API keep working; wrap `select_related`/`prefetch_related` calls in the existing try/except style.
- **No `order_types`/`items` sheets for Order's with-related export** — `order_types` is an M2M field and `items` a reverse FK, neither a forward FK/OneToOne, so `get_related_targets` (forward FK/OneToOne only) already excludes both. Unchanged behavior.

## Risks / Trade-offs

- [Risk] Clearing prefetch could hide a future need for prefetched M2M columns → Mitigation: `columns_for_model` only reads concrete fields; if M2M export is ever added, revisit explicitly (spec would change).
- [Risk] `chunk_size=2000` on SQLite with multi-relation prefetch could hit `IN`-clause limits → Mitigation: Order now carries two prefetches, but both are cleared before iterating, so the limit doesn't apply; chunk matches Django default.
- [Risk] `prefetch_related(None)` on a non-queryset iterable → Mitigation: `hasattr` guard + try/except, existing tests cover plain iterables.
