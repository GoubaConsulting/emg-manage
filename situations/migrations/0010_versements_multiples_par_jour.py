from django.db import migrations


def rattacher_distributions_existantes(apps, schema_editor):
    Situation = apps.get_model("situations", "SituationJournaliere")
    Distribution = apps.get_model("distributions", "Distribution")
    database = schema_editor.connection.alias

    for situation in Situation.objects.using(database).filter(actif=True).iterator():
        distributions = Distribution.objects.using(database).filter(
            actif=True,
            distributeur_id=situation.distributeur_id,
            date_distribution=situation.date_situation,
            situation_id__isnull=True,
        )
        if situation.etat == "CLOTUREE":
            distributions = distributions.filter(etat="CLOTUREE")
        else:
            distributions = distributions.filter(
                etat="OUVERTE",
                date_creation__lte=situation.date_creation,
            )
        distributions.update(situation_id=situation.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("situations", "0009_situation_montant_surplus"),
        ("distributions", "0005_distribution_situation"),
    ]

    operations = [
        migrations.RunPython(
            rattacher_distributions_existantes,
            migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="situationjournaliere",
            name="situation_unique_distributeur_date_active",
        ),
    ]
