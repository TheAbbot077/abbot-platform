import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="documents/")),
                ("status", models.CharField(choices=[("uploaded", "Uploaded"), ("extracting_text", "Extracting text"), ("chapters_detected", "Chapters detected"), ("processing_concepts", "Processing concepts"), ("ready", "Ready"), ("failed", "Failed")], default="uploaded", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Chapter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("sequence_number", models.PositiveIntegerField()),
                ("extracted_text", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chapters", to="documents.document")),
            ],
            options={
                "ordering": ["sequence_number"],
            },
        ),
        migrations.CreateModel(
            name="Concept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("sequence_number", models.PositiveIntegerField()),
                ("summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chapter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concepts", to="documents.chapter")),
            ],
            options={
                "ordering": ["chapter__sequence_number", "sequence_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="chapter",
            constraint=models.UniqueConstraint(fields=("document", "sequence_number"), name="unique_chapter_sequence_per_document"),
        ),
        migrations.AddConstraint(
            model_name="chapter",
            constraint=models.CheckConstraint(check=Q(("sequence_number__gte", 1)), name="chapter_sequence_number_starts_at_1"),
        ),
        migrations.AddConstraint(
            model_name="concept",
            constraint=models.UniqueConstraint(fields=("chapter", "sequence_number"), name="unique_concept_sequence_per_chapter"),
        ),
        migrations.AddConstraint(
            model_name="concept",
            constraint=models.CheckConstraint(check=Q(("sequence_number__gte", 1)), name="concept_sequence_number_starts_at_1"),
        ),
    ]
