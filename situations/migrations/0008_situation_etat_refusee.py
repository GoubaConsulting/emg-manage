# Generated manually for EMG MANAGE.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("situations", "0007_situation_etat_attente_validation"),
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
                    ("REFUSEE", "Refusee"),
                    ("CLOTUREE", "Clôturée"),
                ],
                default="OUVERTE",
                max_length=20,
                verbose_name="Etat",
            ),
        ),
    ]
