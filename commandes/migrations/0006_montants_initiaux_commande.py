# Generated manually for EMG MANAGE.

import django.core.validators
from django.db import migrations, models


def initialiser_totaux_existants(apps, schema_editor):
    Commande = apps.get_model("commandes", "Commande")
    LigneCommande = apps.get_model("commandes", "LigneCommande")

    Commande.objects.update(
        montant_total_brut=models.F("montant_brut"),
        montant_total_net=models.F("montant_net"),
    )

    LigneCommande.objects.update(
        montant_total_brut=models.F("montant"),
        montant_total_net=models.F("montant_net"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("commandes", "0005_lignecommande_quantite_distribuee_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="commande",
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
            model_name="commande",
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
            model_name="commande",
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
            model_name="commande",
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
            model_name="lignecommande",
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
            model_name="lignecommande",
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
            model_name="lignecommande",
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
            model_name="lignecommande",
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
