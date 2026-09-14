"""
seed_ourlives_demo — deterministic realistic demo dataset for the ourlives app.

Usage:
    python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25

Builds a believable sales graph (reps, projects, organizations, contacts,
addresses, orders + items, invitation codes) that exercises every calculated
field (OrderSummaryMixin totals, line_total, token counters, usage %) and all
three admin inline families. All generated emails are test-{hex}@gmail.com.

Stdlib only. Deterministic via random.Random(seed). Safe re-runs: `--clear`
wipes only seeded (`Demo ` / `test-`) transactional rows, never lookups.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ourlives.models import (
    AppSettings,
    CodeType,
    Contact,
    ContactType,
    Country,
    Currency,
    InvitationCode,
    Order,
    OrderItem,
    OrderType,
    Organization,
    OrganizationAddress,
    Product,
    Project,
    Rep,
)

DEMO_PREFIX = "Demo "
EMAIL_PREFIX = "test-"
EMAIL_DOMAIN = "@gmail.com"

FIRST_NAMES = [
    "Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Ruby", "Lucas",
    "Ivy", "Mason", "Ella", "Oliver", "Nora", "Henry", "Lily", "Jack",
]
LAST_NAMES = [
    "Carter", "Nguyen", "Patel", "Garcia", "Kim", "Muller", "Rossi",
    "Dubois", "Silva", "Tanaka", "Novak", "Larsen", "Costa", "Weber",
]
ORG_BASES = [
    "Acme Health", "Northwind Labs", "Globex Care", "Initech Diagnostics",
    "Umbrella Clinics", "Hooli Med", "Stark Imaging", "Wayne Diagnostics",
    "Massive Dynamic Labs", "Cyberdyne Health", "Tyrell Optics", "Aperture Scans",
]
PROJECT_NAMES = ["Demo OurLens Launch", "Demo Regional Pilot", "Demo Enterprise Rollout"]
STREETS = ["12 High Street", "48 Market Road", "7 Station Avenue", "23 Park Lane", "91 River Street"]
CITIES = ["London", "Manchester", "Bristol", "Leeds", "Glasgow", "Cardiff"]
SALES_NOTES = [
    "Met at annual screening conference; wants pilot before flu season.",
    "Renewal likely — asked about enterprise tier pricing.",
    "Referred by Northwind Labs; fast-track onboarding requested.",
    "Procurement needs PO on invoice; 30-day terms agreed.",
    "",
]
REFERRERS = ["Northwind Labs", "Acme Health", "Beta Holdings Ltd", "MedSupply Co"]

# Frozen item prices by product tier (fixture Product.unit_price is 0.00).
TIER_PRICE_RANGE = {
    "micro": (295, 995),
    "regional": (1500, 3995),
    "enterprise": (4500, 9500),
}


class Command(BaseCommand):
    help = "Seed a deterministic realistic ourlives demo dataset (sales-like)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--reps", type=int, default=6)
        parser.add_argument("--orgs", type=int, default=10)
        parser.add_argument("--orders", type=int, default=25)
        parser.add_argument("--tokens", type=int, default=None,
                            help="Override AppSettings.total_tokens target.")
        parser.add_argument("--clear", action="store_true",
                            help="Wipe seeded Demo/test- rows before seeding.")

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        n_reps = options["reps"]
        n_orgs = options["orgs"]
        n_orders = options["orders"]
        email_seq = [0]

        def demo_email():
            email_seq[0] += 1
            return f"{EMAIL_PREFIX}{rng.getrandbits(32):08x}{email_seq[0]:04x}{EMAIL_DOMAIN}"

        call_command("base_loaddata")

        if options["clear"]:
            self._clear_demo()

        with transaction.atomic():
            reps = self._seed_reps(rng, demo_email, n_reps)
            projects = self._seed_projects()
            orgs = self._seed_orgs(rng, demo_email, reps, n_orgs)
            self._seed_contacts_addresses(rng, demo_email, orgs)
            orders = self._seed_orders(rng, orgs, reps, n_orders)
            self._spread_submitted_at(rng, orders)
            self._seed_items(rng, orders)
            n_codes = self._seed_codes(rng, projects, orgs, orders, options.get("tokens"))

        self.stdout.write(self.style.SUCCESS(
            f"Seeded demo data: {len(reps)} reps, {len(orgs)} orgs, "
            f"{len(orders)} orders, {n_codes} codes (seed={options['seed']})."
        ))

    # -- scoped wipe ------------------------------------------------------
    def _clear_demo(self):
        InvitationCode.objects.filter(
            organization__name__startswith=DEMO_PREFIX).delete()
        OrderItem.objects.filter(
            order__organization__name__startswith=DEMO_PREFIX).delete()
        Order.objects.filter(
            organization__name__startswith=DEMO_PREFIX).delete()
        Contact.objects.filter(
            organization__name__startswith=DEMO_PREFIX).delete()
        OrganizationAddress.objects.filter(
            organization__name__startswith=DEMO_PREFIX).delete()
        Organization.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Project.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Rep.objects.filter(email__startswith=EMAIL_PREFIX).delete()
        self.stdout.write("Cleared seeded demo rows (lookups untouched).")

    # -- lookups ----------------------------------------------------------
    def _seed_reps(self, rng, demo_email, n_reps):
        reps = []
        lone, _ = Rep.objects.get_or_create(
            email="test-0000000000000001@gmail.com",
            defaults={"first_name": "Lone", "last_name": "Rep"},
        )
        reps.append(lone)
        i = 0
        while len(reps) < n_reps:
            email = demo_email()
            rep, _ = Rep.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": rng.choice(FIRST_NAMES),
                    "last_name": rng.choice(LAST_NAMES),
                },
            )
            if rep not in reps:
                reps.append(rep)
            i += 1
            if i > n_reps * 10:  # pragma: no cover - safety valve
                break
        return reps

    def _seed_projects(self):
        return [
            Project.objects.get_or_create(
                name=name, defaults={"description": f"Demo sales project {name}"}
            )[0]
            for name in PROJECT_NAMES
        ]

    def _seed_orgs(self, rng, demo_email, reps, n_orgs):
        del demo_email  # orgs carry no email; contacts do
        orgs = []
        empty_org, _ = Organization.objects.get_or_create(
            name="Demo Empty Org",
            defaults={"description": "Showcase org with no orders",
                      "assigned_rep": reps[0]},
        )
        full_org, _ = Organization.objects.get_or_create(
            name="Demo Full Org",
            defaults={"description": "Showcase org with the most orders",
                      "assigned_rep": reps[1] if len(reps) > 1 else reps[0]},
        )
        orgs.extend([empty_org, full_org])
        i = 0
        while len(orgs) < n_orgs:
            base = ORG_BASES[i % len(ORG_BASES)]
            name = f"Demo {base}" if i < len(ORG_BASES) else f"Demo {base} {i}"
            assigned = rng.choice(reps[1:] or reps) if rng.random() < 0.8 else None
            org, _ = Organization.objects.get_or_create(
                name=name,
                defaults={"description": f"Demo client {base}",
                          "assigned_rep": assigned},
            )
            if org not in orgs:
                orgs.append(org)
            i += 1
        return orgs

    def _seed_contacts_addresses(self, rng, demo_email, orgs):
        contact_types = list(ContactType.objects.all())
        countries = list(Country.objects.filter(active=True))
        for org in orgs:
            if org.name == "Demo Empty Org":
                continue
            n_contacts = rng.choice([1, 2, 2, 3])
            for _ in range(n_contacts):
                Contact.objects.get_or_create(
                    organization=org, email=demo_email(),
                    defaults={
                        "contact_type": rng.choice(contact_types),
                        "first_name": rng.choice(FIRST_NAMES),
                        "last_name": rng.choice(LAST_NAMES),
                        "phone": f"+44 7700 {rng.randint(100000, 999999)}",
                    },
                )
            for idx in range(rng.choice([1, 1, 2])):
                OrganizationAddress.objects.get_or_create(
                    organization=org, line1=rng.choice(STREETS),
                    city=rng.choice(CITIES),
                    defaults={
                        "country": rng.choice(countries),
                        "zip": f"{rng.choice(CITIES)[:2].upper()}{rng.randint(1, 20)} "
                               f"{rng.randint(1, 9)}AB",
                        "is_primary": idx == 0,
                    },
                )

    # -- orders -----------------------------------------------------------
    def _seed_orders(self, rng, orgs, reps, n_orders):
        currencies = {c.code: c for c in Currency.objects.all()}
        pilot = OrderType.objects.get(code="pilot")
        standard = OrderType.objects.get(code="standard")
        others = [t for t in OrderType.objects.all() if t.code not in ("pilot", "standard")]
        orderable = [o for o in orgs if o.name != "Demo Empty Org"]
        full_org = next(o for o in orgs if o.name == "Demo Full Org")
        n_full = max(4, n_orders // 3)

        showcase = self._showcase_order_specs(
            currencies, pilot, standard, orderable, full_org)
        orders = [self._create_order(rng, currencies, pilot, standard, others,
                                     orderable, reps, **spec)
                  for spec in showcase]

        remaining = n_orders - len(orders)
        full_left = n_full - sum(1 for o in orders if o.organization_id == full_org.pk)
        for i in range(remaining):
            if full_left > 0 and (i % 3 == 0 or remaining - i <= full_left):
                org = full_org
                full_left -= 1
            else:
                org = rng.choice(orderable)
            orders.append(self._create_order(
                rng, currencies, pilot, standard, others, orderable, reps,
                org=org, index=len(orders)))
        return orders

    def _showcase_order_specs(self, currencies, pilot, standard, orderable, full_org):
        """Fixed rows guaranteeing every calculated-field branch."""
        usd, eur, gbp = currencies["USD"], currencies["EUR"], currencies["GBP"]
        return [
            # currency wins over pilot_currency (must count USD)
            {"org": full_org, "currency": usd, "pilot_currency": gbp,
             "scans": 500, "cost": Decimal("3.50"), "types": [pilot], "index": 0},
            # pilot_currency only (must count GBP)
            {"org": full_org, "currency": None, "pilot_currency": gbp,
             "scans": 100, "cost": Decimal("8.00"), "types": [pilot], "index": 1},
            # neither currency (must count Uncategorized)
            {"org": orderable[-1], "currency": None, "pilot_currency": None,
             "scans": 50, "cost": Decimal("30.00"), "types": [standard], "index": 2},
            # null scans + null cost branches
            {"org": orderable[-1], "currency": usd,
             "scans": None, "cost": Decimal("2.50"), "types": [standard], "index": 3},
            {"org": orderable[-1], "currency": eur,
             "scans": 200, "cost": None, "types": [], "index": 4},
        ]

    def _create_order(self, rng, currencies, pilot, standard, others,
                      orderable, reps, org=None, currency="__random__",
                      pilot_currency="__random__", scans="__random__",
                      cost="__random__", types="__random__", index=0):
        org = org or rng.choice(orderable)
        if currency == "__random__":
            currency = rng.choice(
                [currencies["USD"], currencies["USD"], currencies["EUR"],
                 currencies["GBP"], currencies["CAD"], currencies["ZAR"], None])
        if pilot_currency == "__random__":
            pilot_currency = rng.choice(
                [None, None, None, currencies["GBP"], currencies["USD"]])
        if scans == "__random__":
            scans = None if rng.random() < 0.1 else rng.randint(10, 2000)
        if cost == "__random__":
            cost = None if rng.random() < 0.1 else Decimal(
                f"{rng.uniform(0.5, 12.0):.2f}")
        if types == "__random__":
            roll = rng.random()
            if roll < 0.3:
                types = [pilot]
            elif roll < 0.7:
                types = [standard]
            elif roll < 0.8:
                types = [pilot, standard]
            elif roll < 0.9:
                types = [rng.choice(others)] if others else []
            else:
                types = []
        contacts = list(org.contacts.all())
        rep = org.assigned_rep if org.assigned_rep_id else rng.choice(reps[1:] or reps)
        order = Order.objects.create(
            organization=org,
            rep=rep,
            primary_contact=rng.choice(contacts) if contacts and rng.random() < 0.7 else None,
            invoice_contact=rng.choice(contacts) if contacts and rng.random() < 0.5 else None,
            currency=currency,
            pilot_currency=pilot_currency,
            is_upgrade_from_pilot=bool(types and pilot in types and rng.random() < 0.3),
            is_referral_order=rng.random() < 0.15,
            referral_organisation=rng.choice(REFERRERS) if rng.random() < 0.15 else None,
            po_number=f"PO-2025-{rng.randint(1, 9999):04d}-{index}",
            number_of_scans=scans,
            cost_per_scan=cost,
            additional_information=rng.choice(SALES_NOTES),
            hcaptcha_verified=rng.random() < 0.8,
        )
        if types:
            order.order_types.add(*types)
        return order

    def _spread_submitted_at(self, rng, orders):
        now = timezone.now()
        for order in orders:
            submitted = now - timedelta(
                days=rng.randint(0, 180),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            Order.objects.filter(pk=order.pk).update(submitted_at=submitted)

    # -- items ------------------------------------------------------------
    def _seed_items(self, rng, orders):
        products = list(Product.objects.select_related("currency").all())
        usd = Currency.objects.get(code="USD")
        by_code = {}
        for p in products:
            by_code.setdefault(p.currency.code, []).append(p)
        for i, order in enumerate(orders):
            if i == 0:
                # Showcase: order currency (USD) beats product currency (EUR).
                eur_product = rng.choice(by_code.get("EUR", products))
                OrderItem.objects.create(
                    order=order, product=eur_product,
                    quantity=2, unit_price=Decimal("1495.00"))
                continue
            roll = rng.random()
            n_items = 0 if roll < 0.1 else 1 if roll < 0.4 else 2 if roll < 0.7 else 3 if roll < 0.9 else 4
            for _ in range(n_items):
                product = rng.choice(products)
                lo, hi = TIER_PRICE_RANGE.get(product.tier or "micro", (295, 995))
                OrderItem.objects.create(
                    order=order, product=product,
                    quantity=rng.randint(1, 5),
                    unit_price=Decimal(f"{rng.uniform(lo, hi):.2f}"))
        # Showcase: duplicate product lines on one order with items.
        target = next((o for o in orders[1:]
                       if o.items.count() >= 1 and o.currency_id == usd.pk), None)
        if target is None:
            target = next(o for o in orders[1:] if o.items.count() >= 1)
        if target is not None:
            first = target.items.first()
            OrderItem.objects.create(
                order=target, product=first.product,
                quantity=1, unit_price=first.unit_price)

    # -- codes ------------------------------------------------------------
    def _seed_codes(self, rng, projects, orgs, orders, tokens_override):
        code_types = list(CodeType.objects.all())
        specs = []
        for i, order in enumerate(orders):
            n = 0 if i % 4 == 3 else rng.choice([1, 1, 2])
            for _ in range(n):
                specs.append(self._code_spec(
                    rng, projects, code_types, order.organization, order, i,
                    force_usage=None))
        # Orphan codes (no order) + forced usage spread + one inactive.
        for i in range(3):
            specs.append(self._code_spec(
                rng, projects, code_types, rng.choice(orgs), None,
                100 + i, force_usage=[0, "partial", "full"][i]))
        specs.append(self._code_spec(
            rng, projects, code_types, orgs[1], orders[0] if orders else None,
            200, force_usage="partial", inactive=True))

        planned = sum(s["max_use"] for s in specs)
        assigned = InvitationCode.objects.aggregate(
            total=Sum("max_use"))["total"] or 0
        settings = AppSettings.get_solo()
        if tokens_override is not None:
            if assigned + planned > max(settings.total_tokens, tokens_override):
                raise CommandError(
                    f"Not enough tokens. Needed {assigned + planned}, "
                    f"have {max(settings.total_tokens, tokens_override)}.")
            target = max(settings.total_tokens, tokens_override)
        else:
            target = max(settings.total_tokens, assigned + planned)
        if target != settings.total_tokens:
            settings.total_tokens = target
            settings.save()

        for spec in specs:
            InvitationCode.objects.create(**spec)

        total_assigned = InvitationCode.objects.aggregate(
            total=Sum("max_use"))["total"] or 0
        if total_assigned > AppSettings.get_solo().total_tokens:  # pragma: no cover
            raise CommandError("Token pool exceeded after seeding.")
        return len(specs)

    def _code_spec(self, rng, projects, code_types, org, order, seq,
                   force_usage=None, inactive=False):
        max_use = rng.choice([5, 10, 10, 20, 25, 50])
        if force_usage == 0:
            current_use = 0
        elif force_usage == "full":
            current_use = max_use
        elif force_usage == "partial":
            current_use = max(1, max_use // 3)
        else:
            roll = rng.random()
            current_use = 0 if roll < 0.4 else max_use if roll < 0.55 else rng.randint(1, max_use - 1)
        return {
            "project": rng.choice(projects),
            "organization": org,
            "is_active": False if inactive else rng.random() < 0.9,
            "max_use": max_use,
            "current_use": current_use,
            "order": order,
            "code_type": rng.choice(code_types) if code_types and rng.random() < 0.8 else None,
            "sequence": rng.randint(1, 20) if rng.random() < 0.7 else None,
        }
