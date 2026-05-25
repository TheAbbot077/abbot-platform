import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0002_concept_is_required_unique_title"),
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuizQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question_text", models.TextField()),
                ("option_a", models.CharField(max_length=500)),
                ("option_b", models.CharField(max_length=500)),
                ("option_c", models.CharField(max_length=500)),
                ("option_d", models.CharField(max_length=500)),
                ("correct_option", models.CharField(choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], max_length=1)),
                ("explanation", models.TextField()),
                ("is_answered", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_questions", to="documents.concept")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
