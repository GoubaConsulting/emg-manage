from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("distributions", "0004_montants_initiaux_distribution"),
        ("situations", "0009_situation_montant_surplus"),
    ]

    operations = [
        migrations.AddField(
            model_name="distribution",
            name="situation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="distributions",
                to="situations.situationjournaliere",
                verbose_name="Versement",
            ),
        ),
    ]
