## ADDED Requirements

### Requirement: Manual sidebar navigation groups

`UNFOLD["SIDEBAR"]` SHALL set `show_all_applications=False`, `show_search=True`, and a `navigation` list with exactly four groups in order: (1) operational ourlives models — `Project`, `Organization`, `InvitationCode`, `Order`, `Rep`, `AppSettings` (`admin:ourlives_appsettings_change`), `StripeEvent`; (2) collapsible **Reference data** (`collapsible=True`, separator) — `Country`, `ContactType`, `CodeType`, `OrderType`, `Currency`, `Product`; (3) **Credits** with the existing Purchase Credits link (`/admin/ourlives/appsettings/purchase/`, permission `ourlives.admin.can_purchase`); (4) explicit **Core** group — `Brand`, `User`, `Group`, `TokenProxy` changelists. Each model item SHALL link via `reverse_lazy("admin:<app_label>_<model_name>_changelist")`, reuse its `ModelAdmin.sidebar_icon`, and declare a `permission` callback requiring `view_<model>` (lambdas of the same shape as `ourlives.admin.can_purchase`).

#### Scenario: Superuser sees all four groups

- **WHEN** a superuser loads any admin page
- **THEN** the sidebar shows the operational group, a collapsible Reference data group, Credits, and Core, each entry linking to its changelist with active-highlighting on the current model

#### Scenario: Limited-permission user sees only permitted links

- **WHEN** a staff user with only `ourlives.view_country` (plus login) loads any admin page
- **THEN** the only ourlives model link rendered is Countries; all other ourlives items are hidden by their permission callbacks while Core items follow the same rule

#### Scenario: Cross-app user sees no ourlives data

- **WHEN** a staff user with permissions only for another app (zero `ourlives` model perms, no `ourlives` module perms) uses the admin
- **THEN** no ourlives changelist links render, direct ourlives changelist URLs return 403, purchase/export endpoints deny access, and the other app's entries render normally (group headers with zero permitted items may still render as empty shells — accepted cosmetic limitation)

### Requirement: Sidebar registry coverage test

The test suite SHALL assert that every model registered in the Django admin has exactly one corresponding entry in `UNFOLD["SIDEBAR"]["navigation"]` (matched by changelist URL), so adding a `ModelAdmin` without a nav entry fails loudly instead of hiding silently.

#### Scenario: Missing nav entry fails

- **WHEN** a developer registers a new `ModelAdmin` without adding a sidebar item
- **THEN** the coverage test fails naming the uncovered model
