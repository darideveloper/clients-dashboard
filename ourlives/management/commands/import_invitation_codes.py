"""
import_invitation_codes — Bulk import invitation codes from a CSV file.

Usage:
    python manage.py import_invitation_codes --project <name> --organization <name> --csv <path>

CSV format (required columns):
    code, is_active, max_use_rate, current_use_rate

The `api_token` column is ignored if present.

Column mapping:
    CSV column          → Model field
    ───────────────────────────────────
    code               → code
    is_active          → is_active
    max_use_rate       → max_use
    current_use_rate   → current_use

Behavior:
    - Project and Organization are looked up by name (not ID), so the same
      CSV works across envs.
    - Before inserting, AppSettings.total_tokens is bumped if the CSV's total
      max_use_rate exceeds the current pool. The old and new values are reported.
    - All rows are validated upfront (types, current ≤ max, required columns).
    - New codes are bulk-created in a single batch.  If any code already exists
      (unique constraint violation), the command falls back to per-row upsert
      (update_or_create) so existing codes are overwritten.
    - Re-running the same CSV is idempotent — all codes will be reported as
      "updated" (or "skipped" if nothing changed).
"""

import csv

from django.db import transaction
from django.db.models import Sum
from django.db.utils import IntegrityError
from django.core.management.base import BaseCommand, CommandError

from ourlives.models import AppSettings, InvitationCode, Organization, Project

REQUIRED_COLUMNS = {"code", "is_active", "max_use_rate", "current_use_rate"}


def _boolish(value: str) -> bool:
    """Parse a lenient boolean from a CSV cell. Raises ValueError if unrecognized."""
    v = value.strip().lower()
    if v in ("true", "1", "yes", "t"):
        return True
    if v in ("false", "0", "no", "f"):
        return False
    raise ValueError(f"Not a recognized boolean: {value!r}")


class Command(BaseCommand):
    help = "Bulk-import invitation codes from a CSV file into a project."

    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            "-p",
            required=True,
            help="Name of the project to link codes to.",
        )
        parser.add_argument(
            "--organization",
            "-o",
            required=True,
            help="Name of the organization to link codes to.",
        )
        parser.add_argument(
            "--csv",
            "-c",
            required=True,
            help="Path to the CSV file with invitation codes.",
        )

    def handle(self, *args, **options):
        project_name = options["project"]
        organization_name = options["organization"]
        csv_path = options["csv"]

        # ------------------------------------------------------------------
        # 2.1  CSV file exists / readable
        # ------------------------------------------------------------------
        try:
            fh = open(csv_path, newline="")
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_path}")
        except OSError as exc:
            raise CommandError(f"Cannot read CSV file {csv_path}: {exc}")

        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            fh.close()
            raise CommandError("CSV file is empty (no header row).")

        header = set(reader.fieldnames)
        # ------------------------------------------------------------------
        # 2.2  Required columns
        # ------------------------------------------------------------------
        missing = REQUIRED_COLUMNS - header
        if missing:
            fh.close()
            raise CommandError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {', '.join(reader.fieldnames)}"
            )

        # ------------------------------------------------------------------
        # 2.4  Project lookup
        # ------------------------------------------------------------------
        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            fh.close()
            raise CommandError(f"Project '{project_name}' not found.")

        try:
            organization = Organization.objects.get(name=organization_name)
        except Organization.DoesNotExist:
            fh.close()
            raise CommandError(f"Organization '{organization_name}' not found.")

        # ------------------------------------------------------------------
        # 2.3  Row-level validation
        # ------------------------------------------------------------------
        rows = []
        errors = []

        for i, row in enumerate(reader, start=2):
            line_errors = []

            code = row.get("code", "")
            if not code:
                line_errors.append("code is empty")

            try:
                max_use = int(row["max_use_rate"])
                if max_use <= 0:
                    line_errors.append("max_use_rate must be a positive integer")
            except (ValueError, KeyError):
                line_errors.append("max_use_rate is not a valid integer")

            try:
                current_use = int(row["current_use_rate"])
                if current_use < 0:
                    line_errors.append("current_use_rate is negative")
            except (ValueError, KeyError):
                line_errors.append("current_use_rate is not a valid integer")

            if not line_errors and current_use > max_use:
                line_errors.append(
                    f"current_use_rate ({current_use}) exceeds "
                    f"max_use_rate ({max_use})"
                )

            try:
                is_active = _boolish(row["is_active"])
            except (ValueError, KeyError):
                line_errors.append("is_active is not a valid boolean")

            if line_errors:
                errors.append(f"  Row {i}: {'; '.join(line_errors)}")
                continue

            rows.append(
                {
                    "code": code,
                    "project": project,
                    "organization": organization,
                    "is_active": is_active,
                    "max_use": max_use,
                    "current_use": current_use,
                }
            )

        fh.close()

        if errors:
            self.stderr.write("Validation errors:\n" + "\n".join(errors))
            raise CommandError("CSV contains invalid rows. No data was imported.")

        # ------------------------------------------------------------------
        # 3  Token pool adjustment
        # ------------------------------------------------------------------
        new_tokens = sum(r["max_use"] for r in rows)
        existing_assigned = InvitationCode.objects.aggregate(
            total=Sum("max_use")
        )["total"] or 0
        needed = existing_assigned + new_tokens

        app_settings = AppSettings.get_solo()
        old_tokens = app_settings.total_tokens

        if app_settings.total_tokens < needed:
            app_settings.total_tokens = needed
            app_settings.save()
            self.stdout.write(
                self.style.WARNING(
                    f"AppSettings.total_tokens bumped: {old_tokens} → {needed} "
                    f"(existing={existing_assigned}, new={new_tokens})"
                )
            )
        else:
            self.stdout.write(
                f"Token pool sufficient: {app_settings.total_tokens} available, "
                f"{new_tokens} new + {existing_assigned} existing = {needed} needed"
            )

        # ------------------------------------------------------------------
        # 4  Bulk insert with fallback
        # ------------------------------------------------------------------
        objs = [InvitationCode(**vals) for vals in rows]

        created = 0
        updated = 0
        errors_retry = []

        try:
            with transaction.atomic():
                InvitationCode.objects.bulk_create(objs, ignore_conflicts=False)
            created = len(objs)
        except IntegrityError:
            for obj in objs:
                try:
                    _, was_created = InvitationCode.objects.update_or_create(
                        code=obj.code,
                        defaults={
                            "project": obj.project,
                            "organization": obj.organization,
                            "is_active": obj.is_active,
                            "max_use": obj.max_use,
                            "current_use": obj.current_use,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except Exception as exc:
                    errors_retry.append(f"  {obj.code}: {exc}")

        # ------------------------------------------------------------------
        # 5  Summary
        # ------------------------------------------------------------------
        parts = []
        if created:
            parts.append(f"{created} created")
        if updated:
            parts.append(f"{updated} updated")
        if errors_retry:
            parts.append(f"{len(errors_retry)} errored")

        total_processed = len(objs)
        if parts:
            msg = f"Imported {total_processed} codes: {', '.join(parts)}."
        else:
            msg = f"No codes were imported. Processed {total_processed} rows."

        if errors_retry:
            self.stderr.write("Errors during fallback upsert:\n" + "\n".join(errors_retry))
            self.stdout.write(self.style.WARNING(msg))
        else:
            self.stdout.write(self.style.SUCCESS(msg))

        if old_tokens != app_settings.total_tokens:
            self.stdout.write(
                f"(Token pool was adjusted from {old_tokens} to {app_settings.total_tokens})"
            )