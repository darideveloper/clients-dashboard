from django.contrib.auth.models import User
from django.db import migrations


def backfill_profiles(apps, schema_editor):
    User_model = apps.get_model("auth", "User")
    Profile = apps.get_model("core", "Profile")
    for user in User_model.objects.all():
        Profile.objects.get_or_create(user=user)


def remove_backfilled_profiles(apps, schema_editor):
    Profile = apps.get_model("core", "Profile")
    Profile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_profiles, remove_backfilled_profiles),
    ]
