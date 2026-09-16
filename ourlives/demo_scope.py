"""Shared scope markers for ourlives demo data tooling.

Single source of truth for identifying seeded demo rows, used by both
`seed_ourlives_demo` (creation) and `clean_ourlives_demo` (audit/removal)
so the two can never drift apart:

- Organizations/Projects: ``name`` starts with ``DEMO_PREFIX``
- Reps/Contacts: ``email`` starts with ``EMAIL_PREFIX`` (``test-{hex}@gmail.com``)
- Descendants (contacts, addresses, orders, items, codes): reachable via
  a ``Demo`` organization; orphan codes via their ``Demo`` organization link.

Lookup tables (countries, currencies, products, types) are never demo data.
"""

DEMO_PREFIX = "Demo "
EMAIL_PREFIX = "test-"
EMAIL_DOMAIN = "@gmail.com"
