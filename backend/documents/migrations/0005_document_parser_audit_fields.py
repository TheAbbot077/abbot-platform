from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_subject"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="parser_version",
            field=models.CharField(default="v1", max_length=32),
        ),
        migrations.AddField(
            model_name="document",
            name="parser_strategy",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="parser_confidence_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="parser_warnings",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="document",
            name="parser_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]

