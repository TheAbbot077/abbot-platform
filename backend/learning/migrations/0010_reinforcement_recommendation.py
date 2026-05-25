from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_chapter_metadata"),
        ("learning", "0009_student_ai_spot_quizzes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReinforcementRecommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                (
                    "failed_bloom_level",
                    models.CharField(
                        choices=[
                            ("remember", "Remember"),
                            ("understand", "Understand"),
                            ("apply", "Apply"),
                            ("analyze", "Analyze"),
                            ("evaluate", "Evaluate"),
                            ("create", "Create"),
                        ],
                        default="understand",
                        max_length=32,
                    ),
                ),
                ("student_ai_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("recommended_action", models.CharField(max_length=255)),
                (
                    "priority",
                    models.CharField(
                        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                        default="medium",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reinforcement_recommendations",
                        to="documents.concept",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reinforcement_recommendations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
