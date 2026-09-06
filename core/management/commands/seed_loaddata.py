import os

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand

BASE_FILE = os.path.basename(__file__)


class Command(BaseCommand):
    help = "Load ALL seed fixtures from ALL apps (run once per environment)"

    def handle(self, *args, **options):
        for app_config in apps.get_app_configs():
            self._sync_seed_media(app_config)
            fixture_dir = os.path.join(
                app_config.path, "fixtures", app_config.label, "seed"
            )
            for fixture in self._find_fixtures(fixture_dir):
                try:
                    call_command("loaddata", f"{app_config.label}/seed/{fixture}")
                except Exception as exc:  # noqa: BLE001
                    print(f"Error in {BASE_FILE}: {exc}")
                    continue

    def _find_fixtures(self, fixture_dir):
        if not os.path.isdir(fixture_dir):
            return []
        return sorted(
            name[:-5] for name in os.listdir(fixture_dir) if name.endswith(".json")
        )

    def _sync_seed_media(self, app_config):
        images_dir = os.path.join(
            app_config.path, "fixtures", app_config.label, "seed", "images"
        )
        if not os.path.isdir(images_dir):
            return
        for root, _, files in os.walk(images_dir):
            for name in files:
                source_path = os.path.join(root, name)
                relative_path = os.path.relpath(source_path, images_dir)
                if default_storage.exists(relative_path):
                    continue
                with open(source_path, "rb") as source_file:
                    default_storage.save(relative_path, source_file)
