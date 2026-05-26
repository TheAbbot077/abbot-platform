from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.db.models import Q


class DocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    EXTRACTING_TEXT = "extracting_text", "Extracting text"
    CHAPTERS_DETECTED = "chapters_detected", "Chapters detected"
    PROCESSING_CONCEPTS = "processing_concepts", "Processing concepts"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class ContentClassification(models.TextChoices):
    TEXTBOOK = "textbook", "Textbook"
    NOVEL = "novel", "Novel"
    PLAY = "play", "Play"
    POEM = "poem", "Poem"
    SHORT_STORY = "short_story", "Short story"
    LITERATURE_TEXTBOOK = "literature_textbook", "Literature textbook"
    UNKNOWN = "unknown", "Unknown"


class DocumentStorageBackend(models.TextChoices):
    LOCAL = "local", "Local file storage"
    R2 = "r2", "Cloudflare R2"


class Subject(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "owner", name="unique_subject_name_per_owner"),
        ]

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, related_name="documents", null=True, blank=True)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/", blank=True)
    storage_backend = models.CharField(
        max_length=16,
        choices=DocumentStorageBackend.choices,
        default=DocumentStorageBackend.LOCAL,
    )
    r2_object_key = models.CharField(max_length=512, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, choices=DocumentStatus.choices, default=DocumentStatus.UPLOADED)
    parser_version = models.CharField(max_length=32, default="v1")
    parser_strategy = models.CharField(max_length=120, blank=True, null=True)
    parser_confidence_score = models.FloatField(blank=True, null=True)
    parser_warnings = models.JSONField(default=list, blank=True)
    parser_metadata = models.JSONField(default=dict, blank=True)
    content_classification = models.CharField(
        max_length=32,
        choices=ContentClassification.choices,
        default=ContentClassification.UNKNOWN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Chapter(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=255)
    sequence_number = models.PositiveIntegerField()
    extracted_text = models.TextField(blank=True)
    chapter_summary = models.TextField(blank=True)
    chapter_objectives = models.JSONField(default=list, blank=True)
    literary_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["document", "sequence_number"], name="unique_chapter_sequence_per_document"),
            models.CheckConstraint(check=Q(sequence_number__gte=1), name="chapter_sequence_number_starts_at_1"),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} - {self.sequence_number}. {self.title}"


class Concept(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="concepts")
    title = models.CharField(max_length=255)
    sequence_number = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["chapter__sequence_number", "sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["chapter", "sequence_number"], name="unique_concept_sequence_per_chapter"),
            models.UniqueConstraint(Lower("title"), "chapter", name="unique_concept_title_per_chapter"),
            models.CheckConstraint(check=Q(sequence_number__gte=1), name="concept_sequence_number_starts_at_1"),
        ]

    def __str__(self) -> str:
        return f"{self.chapter.sequence_number}.{self.sequence_number} {self.title}"
