## Context

`AppSettings` is a singleton model (`django-solo`) in `ourlives/models.py` that holds app-wide configuration. Its admin (`AppSettingsAdmin`) is already registered with fieldsets for token pool, pricing, Stripe, and status display. The admin follows an existing pattern of restricting sensitive actions to superusers — `sync_stripe_price_link` returns `"-"` and `sync_stripe_price_view` returns 403 unless `request.user.is_superuser`.

Two new fields, `api_key` and `storage_base_url`, need to be added to AppSettings. These are credentials/infrastructure URLs that engineers (superusers) should be able to edit at runtime without a deploy, but non-superuser staff should only see.

## Goals / Non-Goals

**Goals:**
- Add `api_key` (plain-text credential) and `storage_base_url` (URL) to the AppSettings model
- Display them in a labeled fieldset in the existing admin form
- Superusers can edit them; other staff can view but not modify
- Generate the migration automatically

**Non-Goals:**
- No encryption-at-rest for `api_key` (follows existing pattern — Stripe keys are in env vars, not DB)
- No new permissions, groups, or custom admin views
- No API endpoints to read/write these fields

## Decisions

| Decision | Choice | Alternatives Considered |
|---|---|---|
| Field types | `CharField` for `api_key`, `URLField` for `storage_base_url` | `CharField` considered but rejected — URL validation at the model layer is desirable for a storage endpoint |
| Restriction mechanism | `get_readonly_fields` dynamic override checking `request.user.is_superuser` | Custom form with per-field permission (overkill for 2 fields); `get_fieldsets` to hide entirely (less transparent); `has_change_permission` at model level (locks whole model) |
| Fieldset grouping | New "API Configuration" section alongside existing Token Pool / Pricing / Stripe / Status | Adding to an existing section (no logical home) |
| Key visibility | Visible but read-only for non-superusers | Hidden entirely (confusing — field shows up then disappears) |

## Risks / Trade-offs

- **api_key stored in plain text** — Same as existing fields (stripe_product_id, etc.). No secret-management infrastructure exists in this project for admin-entered keys. Acceptable given scope.
- **storage_base_url as URLField** — Enforces URL format at the model layer via Django's `URLValidator`. If the value ever comes from a scheme-less origin, the field will reject it.
- **No test coverage for superuser gate** — If the project has admin tests, they should verify non-superusers see the field as read-only. Noted in tasks.
