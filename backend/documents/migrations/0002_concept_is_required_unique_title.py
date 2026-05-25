from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="concept",
            name="is_required",
            field=models.BooleanField(default=True),
        ),
        migrations.AddConstraint(
            model_name="concept",
            constraint=models.UniqueConstraint(Lower("title"), "chapter", name="unique_concept_title_per_chapter"),
        ),
    ]
