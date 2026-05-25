from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0006_bloom_mastery"),
    ]

    operations = [
        migrations.AddField(
            model_name="conceptmastery",
            name="forgetting_rate",
            field=models.DecimalField(decimal_places=5, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name="conceptmastery",
            name="last_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="conceptmastery",
            name="mastery_score",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="conceptmastery",
            name="mastery_strength",
            field=models.CharField(
                choices=[("fast", "Fast"), ("medium", "Medium"), ("slow", "Slow")],
                default="fast",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="conceptmastery",
            name="next_review_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
