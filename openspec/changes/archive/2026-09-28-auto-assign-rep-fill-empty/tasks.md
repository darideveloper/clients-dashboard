## 1. Implementation

- [x] 1.1 Add fill-if-empty assignment in `ingest()` (`ourlives/ingestion.py`): after rep resolution, set `org.assigned_rep = rep` when `org.assigned_rep_id is None` (no migration — nullable FK already exists)
- [x] 1.2 Document the behavior in `ourlives/docs/form-webhook.md` (one line in the org/rep flow)

## 2. Tests + verification

- [x] 2.1 Add tests in `ourlives/test_form_webhook.py`: new order assigns submitting rep to new org; repost by another rep does not overwrite; pre-assigned rep untouched
- [x] 2.2 Run `manage.py test ourlives` green
