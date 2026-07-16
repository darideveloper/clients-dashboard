from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ourlives", "0005_backfill_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitationcode",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="ourlives.organization",
            ),
        ),
    ]
