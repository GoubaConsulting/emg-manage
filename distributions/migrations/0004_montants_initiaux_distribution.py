# Generated manually for EMG MANAGE.

import django.core.validators
from django.db import migrations, models


def initialiser_totaux_existants(apps, schema_editor):
    Distribution = apps.get_model("distributions", "Distribution")
    LigneDistribution = apps.get_model("distributions", "LigneDistribution")

    Distribution.objects.update(
        montant_total_brut=models.F("montant_brut"),
        montant_total_net=models.F("montant_net"),
    )

    LigneDistribution.objects.update(
        montant_total_brut=models.F("montant"),
        montant_total_net=models.F("montant_net"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("distributions", "0003_distribution_heure_distribution"),
    ]

    operations = [
        migrations.AddField(
            model_name="distribution",
            name="montant_initial",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
                verbose_name="Montant initial",
            ),
        ),
        migrations.AddField(
            model_name="distribution",
            name="montant_net_initial",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
                verbose_name="Montant net initial",
            ),
        ),
        migrations.AddField(
            model_name="distribution",
            name="montant_total_brut",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
                verbose_name="Montant total brut",
            ),
        ),
        migrations.AddField(
            model_name="distribution",
            name="montant_total_net",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
                verbose_name="Montant total net",
            ),
        ),
        migrations.AddField(
            model_name="lignedistribution",
            name="montant_initial",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="lignedistribution",
            name="montant_net_initial",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="lignedistribution",
            name="montant_total_brut",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="lignedistribution",
            name="montant_total_net",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
        migrations.RunPython(
            initialiser_totaux_existants,
            migrations.RunPython.noop,
        ),
    ]
