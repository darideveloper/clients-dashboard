## Context

`Order` (`ourlives/models.py`) holds billing milestones (`invoice_sent/_on`, `invoice_paid/_on`, `commission_paid/_on`) rendered as same-row pairs in the `Billing` fieldset of `OrderAdmin` (`ourlives/admin.py`). There is no field for the commission terms themselves (rate/amount agreed with the rep). Prior art: short free-text fields (`referral_organisation`, `po_number`) use `CharField(max_length=255, blank=True)`.

## Goals / Non-Goals

**Goals:**
- Persist a short free-text rep commission note per order.
- Render it as a single-line text input on its own row in the Billing section, after the commission pair.

**Non-Goals:**
- No list columns, filters, search, ordering changes.
- No validation, parsing, or computation on the note content (it is a human reminder, not a number).
- No currency/amount structure — if summable commissions are ever needed, that is a separate change (DecimalField + migration from text).

## Decisions

- **`rep_commission_note = CharField(max_length=255, blank=True, default="")`** appended after `commission_paid_on`. Rationale: Option A from exploration — short values ("15%", "$500 flat"); `blank=True` keeps it optional with zero backfill risk; follows the `referral_organisation` precedent. Alternative (TextField) rejected — notes are a line at most. Alternative (DecimalField) rejected — user chose free text; structuring is deferred.
- **Admin: own row at end of Billing fieldset** (not paired — a text input is full-width, pairing it with a checkbox would squeeze it). Rationale: readability; keeps the three checkbox+date pairs visually grouped.
- **Migration**: single standard `makemigrations` (default "" fills existing rows).

## Risks / Trade-offs

- [Risk] Free text is unqueryable — a future "total commission per rep" report would need a structured field + text migration → Accepted (documented Non-Goal); the field name (`_note`) signals it is not the amount.
