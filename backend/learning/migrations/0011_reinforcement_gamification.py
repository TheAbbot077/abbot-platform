from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0010_reinforcement_recommendation"),
    ]

    operations = [
        migrations.AddField(
            model_name="reinforcementrecommendation",
            name="friendly_label",
            field=models.CharField(default="Memory refresher", max_length=120),
        ),
        migrations.AddField(
            model_name="reinforcementrecommendation",
            name="friendly_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="reinforcementrecommendation",
            name="mission_title",
            field=models.CharField(default="Daily rescue mission", max_length=160),
        ),
    ]
