from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "theme",
                    models.CharField(
                        choices=[
                            ("black_white_gold", "Black, white and gold"),
                            ("royal_blue_white_gold", "Royal blue, white and gold"),
                            ("green_white_gold", "Green, white and gold"),
                            ("red_white_gold", "Red, white and gold"),
                            ("purple_white_gold", "Purple, white and gold"),
                        ],
                        default="black_white_gold",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "user settings",
                "verbose_name_plural": "user settings",
            },
        ),
    ]
