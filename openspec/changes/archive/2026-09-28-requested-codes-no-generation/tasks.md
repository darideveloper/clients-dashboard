## 1. Model + migration

- [x] 1.1 Add `OrderRequestedCode` model (`order` FK CASCADE `requested_codes`, `sequence`, `value` non-unique, `code_type` FK PROTECT nullable, ordering by order+sequence) and `Order.requested_codes_wanted` / `requested_codes_bundle` / `requested_code_type` fields in `ourlives/models.py`
- [x] 1.2 Create and apply migration (`makemigrations ourlives`, `migrate`)

## 2. Ingestion rewrite

- [x] 2.1 Replace `_create_codes()` call in `ingest()` with requested-codes writer (collect non-empty `code-1..code-20` incl. within-order duplicates, resolve bundle `CodeType`, delete existing requested rows + bulk-insert in `transaction.atomic`, refresh order bundle fields, never touch `tokens_used`)
- [x] 2.2 Remove `tokens_used` accumulation and now-unused imports
- [x] 2.3 Update `ourlives/docs/form-webhook.md` (requested vs. live codes, replace-on-repost, gap preservation, manual-workflow note for creating real codes)

## 3. Admin + export

- [x] 3.1 Register `OrderRequestedCodeAdmin(OurlivesModelAdminBase)` (search `value` + `order__order_number`, filters `code_type` + order) and add tabular inline to `OrderAdmin`
- [x] 3.2 Add readonly live-count display to `OrderAdmin` reading a `_live_codes_count` row-count annotation (`ordering="_live_codes_count"`, `0` for codeless) and show it in `list_display`
- [x] 3.3 Verify full-app export includes the new sheet (no `admin_base` change; manual click-through of "Export all app data")

## 4. Tests + verification

- [x] 4.1 Update `test_webhook_samples.py` (OL-86..94: 0 invitation codes, N requested codes, OL-89 gap `14→16`, OL-93 `up_to_5`, repost replaces, `tokens_used==0`)
- [x] 4.2 Update `test_form_webhook.py` `InvitationCodeTests` → requested-codes equivalents (gap, null bundle, replace-on-repost, pool-exhausted still stores requested rows) + admin test for the live-count display
- [x] 4.3 Run `pytest ourlives/` green and manual webhook replay of OL-89 + OL-93
