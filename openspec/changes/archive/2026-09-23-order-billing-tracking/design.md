## Context

`Order` (`ourlives/models.py:585`) tracks identity, parties, pricing, and boolean flags, but has no billing-milestone state. `OrderAdmin` (`ourlives/admin.py:383`) renders detail via fieldsets (Order / Terms / Details / Related); list views and Excel export flow through `project/admin_base.py` mixins (`OurlivesModelAdminBase`). Explore-phase decisions (user-confirmed): Option B (stored bool + nullable date per milestone), no bool↔date coupling, `DateField` (day granularity), new `Billing` fieldset detail-only.

## Goals / Non-Goals

**Goals:**
- Persist 3 independent billing milestones (invoice sent, invoice paid, rep commission paid), each as manual flag + optional date.
- Render them as native checkbox + Unfold date picker in a dedicated `Billing` section of the Order detail page.

**Non-Goals:**
- No list columns, filters, search, ordering, or sidebar changes.
- No auto-tick / auto-date / cross-field validation; no workflow enforcement (e.g. paid requires sent).
- No computed displays, no API/serializer changes.

## Decisions

- **6 plain model fields, no `clean()`**: `invoice_sent = BooleanField(default=False)`, `invoice_sent_on = DateField(null=True, blank=True)`, same pair for `invoice_paid` / `commission_paid`. Rationale: matches the confirmed "fully manual, either side may be set alone" semantics; cheapest schema; keeps admin default widgets (checkbox + date picker) with zero custom form code. Alternative (date-only with derived flags) rejected by user — wants stored checkboxes. Alternative (coupled validation) rejected — user explicitly allows tick-without-date and date-without-tick.
- **Field placement in model**: append after `hcaptcha_verified`, before `Meta`. Rationale: groups new billing state at the end of the field list, keeps diff small, avoids disturbing existing field order.
- **Admin: new `("Billing", {...})` fieldset between `Terms` and `Details`** with the 6 fields grouped as same-row pairs — `("invoice_sent", "invoice_sent_on")`, `("invoice_paid", "invoice_paid_on")`, `("commission_paid", "commission_paid_on")` — so each checkbox renders side by side with its date picker instead of stacked. Rationale: stock Django fieldset behavior (inner tuple = one row), supported by Unfold's per-field row template; detail-only visibility falls out naturally (not added to `list_display`/`list_filter`); dedicated section is scannable vs stuffing into `Terms`. No `readonly_fields` additions — all editable.
- **Migration**: single standard `makemigrations` (no data migration; defaults fill existing rows). Rationale: all fields nullable-blank / default False, so zero backfill risk.

## Risks / Trade-offs

- [Risk] Flag/date disagreement (ticked + empty date, or date + unticked) → Accepted by design (user decision); mitigated by documenting the semantics in spec scenarios so future workflow rules can build on it.
- [Risk] Shared Postgres across worktree siblings → Mitigate by migrating from one sibling at a time (repo worktree runbook).
