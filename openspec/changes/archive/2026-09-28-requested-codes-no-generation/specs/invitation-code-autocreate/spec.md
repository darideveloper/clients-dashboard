## REMOVED Requirements

### Requirement: Invitation codes auto-created from form codes
**Reason**: Paused per client request — form `code-N` values are stored as `OrderRequestedCode` rows instead of live `InvitationCode`s.
**Migration**: No data migration of existing `InvitationCode`s (left untouched). When generation is re-enabled, rebuild the creation path reading from `OrderRequestedCode`.

### Requirement: Token count recorded per order
**Reason**: With no `InvitationCode` creation from the form, there is nothing to accumulate; `Order.tokens_used` is frozen legacy (see `crm-orders` delta: pre-existing values kept, new orders `0`, live count via the existing `_codes_used` annotation in admin).
**Migration**: No data migration. New ingests do not touch `tokens_used`.

### Requirement: Reconcile adds only missing codes
**Reason**: Add-only reconcile protected live `current_use` history; requested codes carry no history and use replace-on-repost instead (see `requested-codes`).
**Migration**: None — existing `InvitationCode`s are never touched by reposts that only carry requested codes.
