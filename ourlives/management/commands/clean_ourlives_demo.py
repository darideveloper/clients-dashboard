"""
clean_ourlives_demo — interactive audit and removal of seeded demo data.

Usage:
    python manage.py clean_ourlives_demo            # preview + prompt per group
    python manage.py clean_ourlives_demo --dry-run  # preview only, delete nothing
    python manage.py clean_ourlives_demo --yes      # delete all Demo groups, no prompts

Prompts per Demo organization (full drill-down with natural identifiers),
then per remaining Demo project and test- rep: (d)elete / (k)eep /
(a)ll remaining / (q)uit / (?)help. Each confirmed group is deleted in its
own transaction in FK-safe order. Lookups, handmade rows, and
AppSettings.total_tokens are never touched. Stdlib only.
"""

import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ourlives.demo_scope import DEMO_PREFIX, EMAIL_PREFIX
from ourlives.models import (
    AppSettings,
    Contact,
    Country,
    InvitationCode,
    Order,
    OrderItem,
    Organization,
    OrganizationAddress,
    Project,
    Rep,
    format_currency_breakdown,
)

HELP = ("(d)elete this group / (k)eep / (a)ll remaining / (q)uit / (?)help")


def demo_orgs():
    return Organization.objects.filter(
        name__startswith=DEMO_PREFIX).order_by("name")


def demo_projects():
    return Project.objects.filter(name__startswith=DEMO_PREFIX).order_by("name")


def demo_reps():
    return Rep.objects.filter(email__startswith=EMAIL_PREFIX).order_by("email")


def org_codes(org):
    return InvitationCode.objects.filter(organization=org)


def org_items(org):
    return OrderItem.objects.filter(order__organization=org)


def usage_str(code):
    if not code.max_use:
        return "—"
    pct = code.current_use / code.max_use * 100
    return f"{code.current_use}/{code.max_use} ({pct:.0f}%)"


class Command(BaseCommand):
    help = "Interactively audit and delete seeded ourlives demo data."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Print the preview table and exit without prompting or deleting.")
        parser.add_argument("--yes", action="store_true",
                            help="Delete all Demo groups without prompting.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        auto_yes = options["yes"]
        if not (dry_run or auto_yes) and not sys.stdin.isatty():
            raise CommandError(
                "clean_ourlives_demo needs an interactive terminal; "
                "use --yes or --dry-run in non-interactive sessions.")

        orgs = list(demo_orgs())
        if not orgs and not demo_projects().exists() and not demo_reps().exists():
            self.stdout.write("No demo data found.")
            return

        deleted = self._empty_counter()
        self._preview(orgs)
        if dry_run:
            self.stdout.write("Dry run — no deletions. Re-run without --dry-run to prompt.")
            return

        mode = {"delete_rest": auto_yes}
        for i, org in enumerate(orgs, start=1):
            action = self._prompt_org(org, i, len(orgs), mode)
            if action == "quit":
                break
            if action == "delete":
                self._accumulate(deleted, self._delete_org(org))

        if mode.get("quit"):
            return self._summary(deleted, "Quit — remaining groups untouched.")
        for project in list(demo_projects()):
            action = self._prompt_project(project, mode)
            if action == "quit":
                break
            if action == "delete":
                self._accumulate(deleted, self._delete_project(project))

        if mode.get("quit"):
            return self._summary(deleted, "Quit — remaining groups untouched.")
        for rep in list(demo_reps()):
            action = self._prompt_rep(rep, mode)
            if action == "quit":
                break
            if action == "delete":
                self._accumulate(deleted, self._delete_rep(rep))

        self._summary(deleted, "Done.")

    # -- preview --------------------------------------------------------
    def _preview(self, orgs):
        self.stdout.write("Found demo data (lookups untouched):\n")
        header = (f"  {'#':>2}  {'Organization':<24} {'Rep':<28} "
                  f"{'Co':>3} {'Ad':>3} {'Or':>3} {'It':>3} {'Codes':>5}  Combined total")
        self.stdout.write(header)
        totals = self._empty_counter()
        for i, org in enumerate(orgs, start=1):
            contacts = org.contacts.count()
            addresses = org.addresses.count()
            orders = org.orders.count()
            items = org_items(org).count()
            codes = org_codes(org).count()
            totals["contacts"] += contacts
            totals["addresses"] += addresses
            totals["orders"] += orders
            totals["items"] += items
            totals["codes"] += codes
            rep_email = org.assigned_rep.email if org.assigned_rep_id else "—"
            self.stdout.write(
                f"  {i:>2}  {org.name:<24} {rep_email:<28} "
                f"{contacts:>3} {addresses:>3} {orders:>3} {items:>3} {codes:>5}  "
                f"{format_currency_breakdown(org.combined_total)}")
        self.stdout.write(
            f"  {len(orgs)} Demo orgs | {totals['contacts']} contacts | "
            f"{totals['addresses']} addresses | {totals['orders']} orders | "
            f"{totals['items']} items | {totals['codes']} codes | "
            f"Countries {Country.objects.count()}")

    # -- prompts ----------------------------------------------------------
    def _ask(self, mode):
        if mode.get("delete_rest"):
            return "a"
        try:
            return input(f"  {HELP}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.stdout.write("")
            return "q"

    def _prompt_loop(self, mode):
        """Return 'delete', 'keep' or 'quit'. Sets mode flags for a/q."""
        while True:
            answer = self._ask(mode)
            if answer == "?":
                self.stdout.write(
                    "  d = delete this group (own transaction) | k = keep | "
                    "a = delete this and all remaining groups | q = quit now")
            elif answer in ("d", "a"):
                if answer == "a":
                    mode["delete_rest"] = True
                return "delete"
            elif answer == "k":
                self.stdout.write("  → kept.")
                return "keep"
            elif answer == "q":
                mode["quit"] = True
                return "quit"
            else:
                self.stdout.write("  Unknown answer, use d/k/a/q (or ?).")

    def _prompt_org(self, org, index, total, mode):
        if mode.get("delete_rest"):
            return "delete"
        rep = org.assigned_rep
        self.stdout.write(
            f"\n[{index}/{total}] {org.name} — "
            f"Rep: {rep.email + f' ({rep})' if rep else '— (unassigned)'}")
        contacts = org.contacts.select_related("contact_type").order_by(
            "last_name", "first_name")
        self.stdout.write(f"  Contacts ({contacts.count()}):")
        for c in contacts:
            self.stdout.write(
                f"    • {c.email} — {c.first_name} {c.last_name} "
                f"({c.contact_type.code}) — {c.phone or '—'}")
        addresses = org.addresses.select_related("country").order_by(
            "-is_primary", "city")
        self.stdout.write(f"  Addresses ({addresses.count()}):")
        for a in addresses:
            self.stdout.write(
                f"    • {a.line1}, {a.city} {a.zip}, {a.country.iso2}"
                f"{' — primary' if a.is_primary else ''}")
        orders = org.orders.select_related(
            "currency", "pilot_currency").order_by("order_number")
        self.stdout.write(f"  Orders ({orders.count()}):")
        for o in orders:
            curr = o.currency.code if o.currency_id else (
                o.pilot_currency.code if o.pilot_currency_id else "No Currency")
            types = ",".join(o.order_types.values_list("code", flat=True)) or "—"
            self.stdout.write(
                f"    • {o.order_number} — {o.po_number} — "
                f"{o.number_of_scans}× {o.cost_per_scan} = "
                f"{curr} {o.total_agreed_price:,.2f} — {types} — "
                f"{o.submitted_at.date()}")
            for item in o.items.select_related("product").all():
                self.stdout.write(
                    f"        — {item.product.name} ×{item.quantity} @ "
                    f"{item.unit_price:,.2f} = {item.line_total:,.2f}")
        codes = org_codes(org).select_related("project", "code_type", "order")
        self.stdout.write(f"  Codes ({codes.count()}):")
        for code in codes:
            self.stdout.write(
                f"    • {code.code} — {code.project.name} — "
                f"{code.code_type.code if code.code_type_id else '—'} — "
                f"{usage_str(code)} — {'active' if code.is_active else 'inactive'} — "
                f"{code.order.order_number if code.order_id else 'orphan'}")
        return self._prompt_loop(mode)

    def _prompt_project(self, project, mode):
        if mode.get("delete_rest"):
            return "delete"
        left = InvitationCode.objects.filter(project=project).count()
        self.stdout.write(f"\n[project] {project.name} — codes left: {left}")
        return self._prompt_loop(mode)

    def _prompt_rep(self, rep, mode):
        if mode.get("delete_rest"):
            return "delete"
        handmade = rep.organizations.exclude(name__startswith=DEMO_PREFIX).count()
        self.stdout.write(
            f"\n[rep] {rep.email} — {rep} — "
            f"{rep.orders.count()} orders, {rep.organizations.count()} orgs"
            f"{f' ({handmade} HANDMADE — deleting only NULLs their rep)' if handmade else ''}")
        return self._prompt_loop(mode)

    # -- deletion ---------------------------------------------------------
    @staticmethod
    def _empty_counter():
        return {"orgs": 0, "projects": 0, "reps": 0, "contacts": 0,
                "addresses": 0, "orders": 0, "items": 0, "codes": 0}

    @staticmethod
    def _accumulate(total, part):
        for key, value in part.items():
            total[key] += value

    def _delete_org(self, org):
        counts = self._empty_counter()
        with transaction.atomic():
            counts["codes"] = org_codes(org).count()
            org_codes(org).delete()
            counts["items"] = org_items(org).count()
            org_items(org).delete()
            counts["orders"] = org.orders.count()
            org.orders.all().delete()
            counts["contacts"] = org.contacts.count()
            org.contacts.all().delete()
            counts["addresses"] = org.addresses.count()
            org.addresses.all().delete()
            org.delete()
            counts["orgs"] = 1
        self.stdout.write(f"  → deleted: {self._describe(counts)} (atomic)")
        return counts

    def _delete_project(self, project):
        counts = self._empty_counter()
        with transaction.atomic():
            linked = InvitationCode.objects.filter(project=project)
            counts["codes"] = linked.count()
            linked.delete()
            project.delete()
            counts["projects"] = 1
        self.stdout.write(f"  → deleted: {self._describe(counts)} (atomic)")
        return counts

    def _delete_rep(self, rep):
        counts = self._empty_counter()
        if rep.orders.exists():
            self.stdout.write(
                f"  → kept: {rep.email} still has {rep.orders.count()} orders "
                "(delete those orgs first).")
            return counts
        with transaction.atomic():
            rep.delete()
            counts["reps"] = 1
        self.stdout.write("  → deleted: 1 rep (atomic)")
        return counts

    @staticmethod
    def _describe(counts):
        parts = [f"{v} {k}" for k, v in counts.items() if v and k != "orgs"
                 and k != "projects" and k != "reps"]
        for key in ("orgs", "projects", "reps"):
            if counts[key]:
                parts.append(f"{counts[key]} {key}")
        return ", ".join(parts) or "nothing"

    def _summary(self, deleted, headline):
        remaining_orgs = demo_orgs().count()
        remaining_projects = demo_projects().count()
        remaining_reps = demo_reps().count()
        settings = AppSettings.get_solo()
        self.stdout.write(
            f"\n{headline} Deleted {self._describe(deleted)}. "
            f"Remaining: {remaining_orgs} Demo orgs, {remaining_projects} "
            f"Demo projects, {remaining_reps} test- reps. "
            f"Countries {Country.objects.count()} untouched. "
            f"Tokens: total {settings.total_tokens} → assigned "
            f"{settings.tokens_assigned} (pool left as-is).")
