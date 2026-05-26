from rest_framework import serializers

from .models import Chapter, Concept, Document, Subject


class SubjectSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name", "document_count", "created_at", "updated_at"]
        read_only_fields = ["id", "document_count", "created_at", "updated_at"]

    def get_document_count(self, subject: Subject) -> int:
        return getattr(subject, "document_count", subject.documents.count())


class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = ["id", "title", "sequence_number", "is_required", "summary", "created_at", "updated_at"]
        read_only_fields = fields


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = [
            "id",
            "title",
            "sequence_number",
            "extracted_text",
            "chapter_summary",
            "chapter_objectives",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Document
        fields = ["id", "subject", "subject_name", "title", "file", "status", "chapters", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "chapters", "created_at", "updated_at"]

    def validate_file(self, uploaded_file):
        if not uploaded_file.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Uploaded file must use a .pdf extension.")

        allowed_content_types = {"application/pdf", "application/octet-stream", "binary/octet-stream", ""}
        if uploaded_file.content_type not in allowed_content_types:
            raise serializers.ValidationError("Only PDF uploads are supported in this MVP.")

        return uploaded_file

    def validate_subject(self, subject):
        if subject and subject.owner != self.context["request"].user:
            raise serializers.ValidationError("Select one of your own subjects.")
        return subject
