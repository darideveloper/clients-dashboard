# Demo clean (`clean_ourlives_demo`)

Interactive audit and removal of seeded demo data (see `demo-seed.md` for what
the seed creates). Prompts per `Demo` organization with a full drill-down,
then per remaining `Demo` project and `test-` rep. Same flow on local and prod.

## Run commands

```bash
python manage.py clean_ourlives_demo
python manage.py clean_ourlives_demo --dry-run
python manage.py clean_ourlives_demo --yes
```

| Invocation | Behavior |
|---|---|
| `python manage.py clean_ourlives_demo` | Preview table, then prompt per group (`d/k/a/q/?`). |
| `python manage.py clean_ourlives_demo --dry-run` | Preview table only. No prompts, no deletions, exit 0. |
| `python manage.py clean_ourlives_demo --yes` | Delete all Demo groups without prompting. Final summary. |

Non-interactive stdin (piped/CI) without `--yes`/`--dry-run` exits with an error.

## Prompt reference

| Key | Meaning |
|---|---|
| `d` | Delete this group (own `transaction.atomic()`). |
| `k` | Keep this group. |
| `a` | Delete this and all remaining groups without further prompts. |
| `q` | Quit now; confirmed deletions stay, the rest is untouched. |
| `?` | Print the legend. |

Per org the prompt shows every related row: contacts (`email — name (type)`),
addresses (`line1, city`), orders (`order_number — PO — totals — types — date`)
with items (`product ×qty @ price = line_total`), codes (`code — project —
usage % — order`). Projects show still-linked code counts; reps show
order/org counts with a HANDMADE warning when linked to non-Demo orgs (a rep
with orders is never deleted — `PROTECT`).

## Scope + safety note

Only `Demo `-prefixed orgs/projects, `test-` reps, and their descendants are
ever deleted, in reverse-FK order (codes → items → orders →
contacts/addresses → org → project/rep). Lookup tables (249 countries,
currencies, products, types), handmade rows, and `AppSettings.total_tokens`
are never touched — freeing happens automatically via
`tokens_available = total − assigned`.
