# Generated manually for EMG MANAGE.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("situations", "0006_situationgerant_lignesituationgerant_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="situationjournaliere",
            name="etat",
            field=models.CharField(
                choices=[
                    ("OUVERTE", "Ouverte"),
                    (
                        "ATTENTE_VALIDATION",
                        "En attente de validation",
                    ),
                    ("CLOTUREE", "Clôturée"),
                ],
                default="OUVERTE",
                max_length=20,
                verbose_name="Etat",
            ),
        ),
    ]
