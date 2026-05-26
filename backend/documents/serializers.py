from rest_framework import serializers

from .models import Chapter, Concept, Document, Subject
from .r2_storage import build_document_object_key, create_presigned_upload_url, r2_is_configured


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
        fields = [
            "id",
            "subject",
            "subject_name",
            "title",
            "file",
            "storage_backend",
            "original_filename",
            "file_size_bytes",
            "status",
            "chapters",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "storage_backend",
            "original_filename",
            "file_size_bytes",
            "status",
            "chapters",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        if not self.instance and not attrs.get("file"):
            raise serializers.ValidationError({"file": "Upload a PDF file."})
        return attrs

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


class DirectUploadRequestSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    file_size_bytes = serializers.IntegerField(min_value=1)

    def validate_filename(self, filename):
        if not filename.lower().endswith(".pdf"):
            raise serializers.ValidationError("Uploaded file must use a .pdf extension.")
        return filename

    def validate_file_size_bytes(self, file_size_bytes):
        from django.conf import settings

        if file_size_bytes > settings.DIRECT_UPLOAD_MAX_SIZE_BYTES:
            raise serializers.ValidationError("This PDF is larger than the current upload limit.")
        return file_size_bytes

    def validate(self, attrs):
        if not r2_is_configured():
            raise serializers.ValidationError("Direct uploads are not configured yet.")
        return attrs

    def create_upload_payload(self, user):
        content_type = self.validated_data.get("content_type") or "application/pdf"
        object_key = build_document_object_key(user.id, self.validated_data["filename"])
        return {
            "upload_url": create_presigned_upload_url(object_key, content_type),
            "object_key": object_key,
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "expires_in_seconds": 15 * 60,
        }


class DirectUploadCompleteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.none(), required=False, allow_null=True)
    object_key = serializers.CharField(max_length=512)
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    file_size_bytes = serializers.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["subject"].queryset = Subject.objects.filter(owner=request.user)

    def validate_filename(self, filename):
        if not filename.lower().endswith(".pdf"):
            raise serializers.ValidationError("Uploaded file must use a .pdf extension.")
        return filename

    def validate_object_key(self, object_key):
        request = self.context["request"]
        expected_prefix = f"documents/user-{request.user.id}/"
        if not object_key.startswith(expected_prefix):
            raise serializers.ValidationError("Upload key does not belong to this user.")
        return object_key

    def validate_file_size_bytes(self, file_size_bytes):
        from django.conf import settings

        if file_size_bytes > settings.DIRECT_UPLOAD_MAX_SIZE_BYTES:
            raise serializers.ValidationError("This PDF is larger than the current upload limit.")
        return file_size_bytes
