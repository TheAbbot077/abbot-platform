from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_chapter_metadata"),
        ("learning", "0005_tutormessage"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="quizquestion",
            name="bloom_level",
            field=models.CharField(
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
        migrations.AddField(
            model_name="quizattempt",
            name="bloom_level_scores",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="ConceptMastery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bloom_level_scores", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "concept",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mastery", to="documents.concept"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concept_mastery", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="conceptmastery",
            constraint=models.UniqueConstraint(fields=("user", "concept"), name="unique_concept_mastery_per_user"),
        ),
    ]
