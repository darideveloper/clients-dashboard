# Ourlens Form Webhook (`POST /webhooks/ourlens/`)

Sales orders captured on the public WordPress site ("Ourlens US Order Form V2",
Formidable form_id 20) are forwarded by n8n to this endpoint, which unpacks the
`mapping` and auto-populates the CRM (Order / Organization / Rep / Contacts /
Address / OrderItem(s) / OrderRequestedCode(s)). No live `InvitationCode` is
ever created here — requested codes are stored verbatim for staff to review.

## Endpoint

- **Path**: `POST /webhooks/ourlens/` (csrf-exempt, POST-only)
- **Content-Type**: `application/json` (any other → `400`)
- **Body**: the n8n payload

## Authentication

A shared secret is **inside the JSON body** — `body.token` must equal
`AppSettings.form_webhook_token` (compared with `secrets.compare_digest`).
A missing/mismatched token → `403` and no rows are written. This deviates from
the DRF `Authorization: Token` convention used elsewhere (see
`docs/django-bruno.local.md`).

## Body

```json
{
  "token": "<shared-secret>",
  "event": "create",
  "mapping": { "...55 descriptive keys..." },
  "webhookUrl": "https://n8n.example.com/webhook/abc",
  "executionMode": "production"
}
```

`event` is informational (`create` today). `mapping` holds the 55 descriptive
keys (OL-86+ contract). `executionMode` is **not** a gate — both `production`
and test/dev submissions are processed; the value is recorded on the audit row.

## Mapping keys (abridged)

| Group | Keys |
|---|---|
| Order | `order-number`, `po-number`, `is-this-a-pilot-order`, `is-this-an-upgrade-from-a-pilot`, `is-this-an-order-following-a-referral`, `name-of-the-organsation-who-is-referring`, `currency` (non-pilot) / `pilot-currency` (pilot), `number-of-scans`, `cost-per-scan`, `please-add-an-additional-information-relating-to-this-order` |
| Rep | `reps-name`, `reps-email` (auto-assigned to the organization when it has none; a set rep is never overwritten) |
| Address | `company-address-purchasing-ourlens-scans` (flattened `line1, line2, city, state, zip, country`) |
| Contacts | primary block: `primary-contact`, `primary-contact-email`, `primary-contact-phone`; invoice block: `invoice-contact`, `invoice-email`, `invoice-contact-phone` |
| Pilot product | region-block by pilot currency: `product-<region>`, `quantity-<region>`, `<region-price-field>` (us/Canada/uk/south-africa) |
| Invitation codes | `code-1`..`code-20` (non-empty → one code; see below), `i-would-like-additional-codes`, `how-many-additional-codes-do-you-require` |

## Requested codes

One `OrderRequestedCode` is stored per non-empty `code-N`, regardless of the
"additional codes" toggle (the values are the source of truth). Within-order
duplicates are kept (one row per slot, e.g. OL-88's five identical values);
`sequence = slot N` (gaps kept, e.g. OL-89 skips `code-15`); `value` has no
uniqueness constraint. The bundle toggle and label are stored on the order
(`requested_codes_wanted`, `requested_codes_bundle`, `requested_code_type`
from `how-many-additional-codes-do-you-require`: `Up to 5 Additional Codes` →
`up_to_5`, `Up to 20 Additional Codes` → `up_to_20`; null when blank), and each
code row carries the same `code_type`. `Order.tokens_used` is frozen legacy
and is never incremented here. No pool impact: availability never changes.

## Manually creating the real codes

Staff create live `InvitationCode`s by hand in admin: `project = ourlens`,
`organization` = the order's organization, link `order`, `code_type` = the
order's bundle, `max_use = 1`. Generate fresh code values — do not retype
placeholder literals verbatim (e.g. repeated `P03TST-`), as `InvitationCode.code`
is globally unique and the second identical value will fail.

## Duplicates / reconcile

`order-number` is stored raw but matched normalized (`OL - 95` ≡ `OL-95`). A
matching existing order is reconciled: core fields refreshed, pilot items
replaced, and requested codes **replaced** with the latest mapping (delete +
re-insert, so the stored set always mirrors the last submission).

## Responses

- `200` — ingested (created or updated), or `rejected` (empty `mapping`, or a
  legacy/malformed `mapping` with no `order-number`; no body — n8n does not
  retry)
- `400` — wrong content-type / unparsable JSON
- `403` — missing/wrong token
- `500` — unexpected ingestion error (audit row recorded with status `error`)

Every accepted request writes a `FormWebhookEvent` audit row (raw payload,
order FK, token, event, execution_mode, status `rejected`/`created`/`updated`/
`error`).

## Sample data

See `ourlives/docs/formidable-sample-data/OL-*.json` for real payloads.