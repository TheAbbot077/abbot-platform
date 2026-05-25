import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChapterProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("locked", "Locked"), ("unlocked", "Unlocked"), ("in_progress", "In progress"), ("mastered", "Mastered")], default="locked", max_length=32)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("mastered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chapter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="student_progress", to="documents.chapter")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chapter_progress", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ConceptProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("locked", "Locked"), ("unlocked", "Unlocked"), ("in_progress", "In progress"), ("mastered", "Mastered")], default="locked", max_length=32)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("mastered_at", models.DateTimeField(blank=True, null=True)),
                ("attempts_count", models.PositiveIntegerField(default=0)),
                ("last_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="student_progress", to="documents.concept")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concept_progress", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="chapterprogress",
            constraint=models.UniqueConstraint(fields=("user", "chapter"), name="unique_chapter_progress_per_user"),
        ),
        migrations.AddConstraint(
            model_name="conceptprogress",
            constraint=models.UniqueConstraint(fields=("user", "concept"), name="unique_concept_progress_per_user"),
        ),
    ]
