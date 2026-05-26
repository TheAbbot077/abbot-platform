from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_content_classification_literary_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(blank=True, upload_to="documents/"),
        ),
        migrations.AddField(
            model_name="document",
            name="storage_backend",
            field=models.CharField(
                choices=[("local", "Local file storage"), ("r2", "Cloudflare R2")],
                default="local",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="r2_object_key",
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AddField(
            model_name="document",
            name="original_filename",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="document",
            name="file_size_bytes",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="content_type",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
