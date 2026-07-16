from django.db import migrations


def backfill_organization(apps, schema_editor):
    Organization = apps.get_model("ourlives", "Organization")
    InvitationCode = apps.get_model("ourlives", "InvitationCode")

    org, _ = Organization.objects.get_or_create(
        name="Legacy", defaults={"description": "Default organization for existing codes"}
    )
    InvitationCode.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ("ourlives", "0004_organization_invitationcode_organization"),
    ]

    operations = [
        migrations.RunPython(backfill_organization, migrations.RunPython.noop),
    ]
