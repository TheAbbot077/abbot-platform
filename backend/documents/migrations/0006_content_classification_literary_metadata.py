from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_document_parser_audit_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="content_classification",
            field=models.CharField(
                choices=[
                    ("textbook", "Textbook"),
                    ("novel", "Novel"),
                    ("play", "Play"),
                    ("poem", "Poem"),
                    ("short_story", "Short story"),
                    ("literature_textbook", "Literature textbook"),
                    ("unknown", "Unknown"),
                ],
                default="unknown",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="chapter",
            name="literary_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
