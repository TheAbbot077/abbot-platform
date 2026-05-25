from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_chapter_metadata"),
        ("learning", "0003_quizattempt"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConceptLesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_excerpt", models.TextField()),
                ("explanation", models.TextField()),
                ("examples", models.JSONField(blank=True, default=list)),
                ("next_action", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "concept",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="documents.concept"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concept_lessons", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="conceptlesson",
            constraint=models.UniqueConstraint(fields=("user", "concept"), name="unique_concept_lesson_per_user"),
        ),
    ]
