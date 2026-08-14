from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("objectif", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="objectif",
            name="objectif_unique",
        ),
    ]
