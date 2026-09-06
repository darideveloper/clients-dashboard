import os

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand

BASE_FILE = os.path.basename(__file__)


class Command(BaseCommand):
    help = "Load ALL base fixtures from ALL apps (run in every build, deploy, test)"

    def handle(self, *args, **options):
        for app_config in apps.get_app_configs():
            fixture_dir = os.path.join(app_config.path, "fixtures", app_config.label)
            for fixture in self._find_fixtures(fixture_dir):
                try:
                    call_command("loaddata", f"{app_config.label}/{fixture}")
                except Exception as exc:  # noqa: BLE001
                    print(f"Error in {BASE_FILE}: {exc}")
                    continue

    def _find_fixtures(self, fixture_dir):
        if not os.path.isdir(fixture_dir):
            return []
        return sorted(
            name[:-5] for name in os.listdir(fixture_dir) if name.endswith(".json")
        )
