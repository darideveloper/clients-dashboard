## Why

Form submissions create (or reuse) the `Organization` and the `Rep` but never link them: `Organization.assigned_rep` stays empty on new orgs, so staff must hand-assign every rep after each order. The submitting rep is known at ingest time — auto-assigning it closes the loop.

## What Changes

- `ingest()` sets `Organization.assigned_rep` to the submitting rep **only when the organization has none** (fill-if-empty). A manually assigned rep is never overwritten by later submissions.
- Applies to both newly created and existing-but-unassigned organizations, on create and on repost-reconcile alike.
- No changes to rep matching (still by `reps-email`), org matching, contacts, items, codes, or audit.

## Capabilities

### New Capabilities

None — this extends the existing match-or-create flow.

### Modified Capabilities

- `crm-auto-match`: new fill-if-empty rep→organization assignment during webhook ingestion.

## Impact

- `ourlives/ingestion.py` (`ingest()`, ~3 lines + save).
- Tests: `ourlives/test_form_webhook.py` (new order assigns rep; repost with another rep does not steal; pre-assigned rep untouched).
- Docs: one line in `ourlives/docs/form-webhook.md` (org/rep section).
