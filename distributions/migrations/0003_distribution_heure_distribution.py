# Generated manually for EMG MANAGE.

from django.db import migrations, models
from django.utils import timezone


def renseigner_heures_existantes(apps, schema_editor):
    Distribution = apps.get_model(
        "distributions",
        "Distribution"
    )

    for distribution in Distribution.objects.filter(
        heure_distribution__isnull=True
    ).exclude(
        date_creation__isnull=True
    ):

        distribution.heure_distribution = (
            timezone.localtime(
                distribution.date_creation
            )
            .time()
            .replace(
                second=0,
                microsecond=0
            )
        )

        distribution.save(
            update_fields=[
                "heure_distribution"
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "distributions",
            "0002_distribution_etat"
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="distribution",
            name="heure_distribution",
            field=models.TimeField(
                blank=True,
                null=True,
                verbose_name="Heure"
            ),
        ),
        migrations.RunPython(
            renseigner_heures_existantes,
            migrations.RunPython.noop
        ),
    ]
