# Demo seed (`seed_ourlives_demo`)

Realistic, deterministic sales-like dataset for the `ourlives` app. It exercises
every calculated field and all three admin inline families. See `crm-erd.md`
for the ER diagram (`ourlives/models.py` is source of truth).

## Run command

```bash
python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25
```

| Flag | Default | Meaning |
|---|---|---|
| `--seed` | `42` | RNG seed. Same seed + flags = same dataset (emails included). |
| `--reps` | `6` | Number of reps (includes 1 showcase rep with no orders). |
| `--orgs` | `10` | Number of organizations (includes Empty + Full showcase orgs). |
| `--orders` | `25` | Number of orders. |
| `--tokens` | (auto) | Override `AppSettings.total_tokens` target. Default sizes the pool to fit planned codes. |
| `--clear` | off | Wipe seeded `Demo ` / `test-` rows first, then reseed. |

The command calls `base_loaddata` first (lookup FK targets), runs inside one
`transaction.atomic()`, uses stdlib RNG only, and gives every rep/contact a
unique `test-{hex}@gmail.com` email.

## What gets created (defaults)

Reps (6, one orderless) → projects (3) → organizations (10, some unassigned
`assigned_rep`) → contacts (1–3 per org, mixed types) + addresses (1–2 per org,
exactly one `is_primary`) → orders (25, contacts from own org, mixed
currencies/types, null scans/cost injection, `submitted_at` spread over
~6 months) → items (0–4 per order, real frozen prices, one duplicate-product
order) → invitation codes (per-order + orphans, 0 %/partial/100 % usage, one
inactive).

## Coverage matrix

| Calculated field / inline | Covered by |
|---|---|
| `agreed_scans_total` (`currency` wins, pilot-only, `No Currency`, nulls → 0) | showcase + random orders |
| `catalog_items_total` (order → pilot → product fallback) | USD order + EUR-product item |
| `combined_total`, `order_count`, `last_order_date` (+ empty `—` states) | Empty Org (0 orders) vs Full Org (most orders) |
| `total_agreed_price`, `is_pilot_order` (pilot/standard/multi/typeless) | order type mix |
| `line_total` + `line_total_display` | non-zero item prices; Order change page |
| `tokens_assigned/used/available`, `usage_percentage` | code usage spread + inactive code |
| `ContactInline`, `OrganizationAddressInline` | Organization change page |
| `OrderItemInline` (0/1/multi items, duplicate line) | Order change page |
| `orders_list`, `companies_list`, `codes_list` (incl. empty states) | Empty Org, lone rep, codeless orders |

`StripeEvent` is intentionally NOT seeded (webhook-only audit rows, read-only
admin).

## `--clear` safety note

`--clear` deletes **only** seeded transactional rows — codes, items, orders,
contacts/addresses, `Demo `-prefixed orgs/projects, and `test-` reps — in
reverse-FK order. Lookup tables (countries, currencies, products, types) and
any handmade rows are never touched.
