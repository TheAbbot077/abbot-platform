from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0011_reinforcement_gamification"),
    ]

    operations = [
        migrations.AddField(
            model_name="conceptlesson",
            name="visual_content",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="tutormessage",
            name="visual_content",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
