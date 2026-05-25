from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_concept_is_required_unique_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="chapter",
            name="chapter_objectives",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="chapter",
            name="chapter_summary",
            field=models.TextField(blank=True),
        ),
    ]
