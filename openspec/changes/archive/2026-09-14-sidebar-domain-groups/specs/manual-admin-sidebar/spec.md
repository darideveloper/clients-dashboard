## MODIFIED Requirements

### Requirement: Manual sidebar navigation groups

`UNFOLD["SIDEBAR"]` SHALL set `show_all_applications=False`, `show_search=True`, and a `navigation` list with exactly six groups in order: (1) operational ourlives models — `Project`, `Organization`, `InvitationCode`, `Order`, `Rep`, `AppSettings` (`admin:ourlives_appsettings_change`), `StripeEvent`; (2) collapsible **Order Data** (`collapsible=True`, separator) — `OrderItem`, `OrderType`; (3) collapsible **Organization Data** (`collapsible=True`, separator) — `Contact`, `OrganizationAddress`, `ContactType`; (4) collapsible **Reference data** (`collapsible=True`, separator) — `Country`, `CodeType`, `Currency`, `Product`; (5) **Credits** with the existing Purchase Credits link (`/admin/ourlives/appsettings/purchase/`, permission `ourlives.admin.can_purchase`); (6) explicit **Core** group — `Brand`, `User`, `Group`, `TokenProxy` changelists. A catalog SHALL live in a domain group iff exactly one model references it and that model's domain has a group (`OrderType`→Order, `ContactType`→Contact); all other catalogs stay in Reference data. Each model item SHALL link via `reverse_lazy("admin:<app_label>_<model_name>_changelist")`, reuse its `ModelAdmin.sidebar_icon`, declare a `permission` callback requiring `view_<model>` (lambdas of the same shape as `ourlives.admin.can_purchase`), and every icon SHALL be unique across the whole navigation.

#### Scenario: Superuser sees all six groups

- **WHEN** a superuser loads any admin page
- **THEN** the sidebar shows the operational group, collapsible Order Data, collapsible Organization Data, collapsible Reference data, Credits, and Core, each entry linking to its changelist with active-highlighting on the current model

#### Scenario: Collapsed domain group auto-opens on its page

- **WHEN** a staff user opens an Order Item changelist while Order Data is collapsed
- **THEN** the Order Data group renders open (Unfold auto-opens the group containing the active item)

#### Scenario: Limited-permission user sees only permitted links

- **WHEN** a staff user with only `ourlives.view_country` (plus login) loads any admin page
- **THEN** the only ourlives model link rendered is Countries; all other ourlives items are hidden by their permission callbacks while Core items follow the same rule

#### Scenario: Cross-app user sees no ourlives data

- **WHEN** a staff user with permissions only for another app (zero `ourlives` model perms, no `ourlives` module perms) uses the admin
- **THEN** no ourlives changelist links render, direct ourlives changelist URLs return 403, purchase/export endpoints deny access, and the other app's entries render normally (group headers with zero permitted items may still render as empty shells — accepted cosmetic limitation)
