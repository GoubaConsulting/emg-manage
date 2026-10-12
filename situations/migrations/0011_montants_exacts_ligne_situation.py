from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("situations", "0010_versements_multiples_par_jour"),
    ]

    operations = [
        migrations.AddField(
            model_name="lignesituationjournaliere",
            name="montant_distribue_brut",
            field=models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="lignesituationjournaliere",
            name="montant_distribue_net",
            field=models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="lignesituationjournaliere",
            name="montant_restant_brut",
            field=models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True),
        ),
    ]
