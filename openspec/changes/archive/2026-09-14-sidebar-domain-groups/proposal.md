## Why

The admin sidebar's single 10-item operational group mixes daily-use parent models (`Organization`, `Order`) with their occasionally-used children (`Contact`, `OrganizationAddress`, `OrderItem`) and type catalogs. Staff scroll past rarely-touched links every day, and Reference data still holds domain-exclusive catalogs (`OrderType`, `ContactType`) far from the models they qualify. Two sidebar icons are also duplicated (`person` for Reps and Users, `key` for Invitation Codes and Tokens), hurting scannability.

## What Changes

- Add a collapsible **Order Data** group (after Our Lives) holding `OrderItem` (moved from Our Lives) and `OrderType` (moved from Reference data). `Order` stays in Our Lives as the main model.
- Add a collapsible **Organization Data** group (after Order Data) holding `Contact` and `OrganizationAddress` (moved from Our Lives) plus `ContactType` (moved from Reference data). `Organization` stays in Our Lives as the main model.
- Our Lives shrinks to the 7 main models; Reference data keeps the shared catalogs (`Country`, `CodeType`, `Currency`, `Product`).
- Fix duplicated icons: `RepAdmin.sidebar_icon` `person` → `badge`, `TokenProxy` admin `key` → `vpn_key` (both valid Material Symbols; Invitation Codes keeps `key`, Users keeps `person`).
- No permission, URL, or admin-behavior changes: per-item `permission` callbacks move verbatim with their items; the registry-coverage invariant (exactly one nav entry per registered model) is preserved.

## Capabilities

### New Capabilities

(none — all behavior lands in existing capabilities)

### Modified Capabilities

- `manual-admin-sidebar`: navigation contract changes from exactly four groups to six, with the new group memberships, order, and icon-uniqueness rule.
- `ourlives-lookup-admin`: `Rep` registration requirement changes `sidebar_icon="person"` → `sidebar_icon="badge"`.

## Impact

- `project/settings.py` (`UNFOLD["SIDEBAR"]["navigation"]` only): 5 item-dict relocations + 2 new group dicts.
- `ourlives/admin.py`: one-line `RepAdmin.sidebar_icon` change; `core/admin.py`: one-line TokenProxy `sidebar_icon` change.
- `ourlives/tests.py`: sidebar assertions only if they pin icons/groups (coverage/permission tests walk groups generically and need no edits).
- No model, migration, permission, or URL changes. Stripe Events placement explicitly out of scope.
