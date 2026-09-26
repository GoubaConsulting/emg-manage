from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("situations", "0008_situation_etat_refusee"),
    ]

    operations = [
        migrations.AddField(
            model_name="situationjournaliere",
            name="montant_surplus",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                validators=[MinValueValidator(0)],
                verbose_name="Montant surplus",
            ),
        ),
    ]
