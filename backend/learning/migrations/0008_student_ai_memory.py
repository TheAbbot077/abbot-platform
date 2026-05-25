from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_chapter_metadata"),
        ("learning", "0007_forgetting_curve"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentAIMemory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("taught_content", models.TextField()),
                ("taught_at", models.DateTimeField()),
                ("initial_mastery_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("current_retention_score", models.DecimalField(decimal_places=2, max_digits=5)),
                (
                    "retention_strength",
                    models.CharField(
                        choices=[("fast", "Fast"), ("medium", "Medium"), ("slow", "Slow")],
                        default="fast",
                        max_length=32,
                    ),
                ),
                ("last_spot_quiz_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_ai_memories",
                        to="documents.concept",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_ai_memories",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="studentaimemory",
            constraint=models.UniqueConstraint(
                fields=("user", "concept"),
                name="unique_student_ai_memory_per_user_concept",
            ),
        ),
    ]
