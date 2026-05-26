from django.db.models import Count
from rest_framework import generics, permissions, response, status, viewsets
from rest_framework.decorators import action

from core.audit import log_admin_action

from .deletion import delete_document_tree
from .models import Concept, Document, DocumentStorageBackend, Subject
from .serializers import (
    ConceptSerializer,
    DirectUploadCompleteSerializer,
    DirectUploadRequestSerializer,
    DocumentSerializer,
    SubjectSerializer,
)
from .tasks import extract_chapters_from_document


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Document.objects.filter(owner=self.request.user)
            .prefetch_related("chapters")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        document = serializer.save(owner=self.request.user)
        extract_chapters_from_document.delay(document.id)

    def perform_destroy(self, instance):
        document_id = instance.id
        title = instance.title
        delete_document_tree(instance)
        log_admin_action(
            request=self.request,
            action="textbook_deleted",
            target_type="document",
            target_id=document_id,
            description=f"User {self.request.user.username} deleted textbook '{title}'.",
            metadata={"title": title, "owner_id": self.request.user.id},
        )

    @action(detail=False, methods=["post"], url_path="direct-upload-url")
    def direct_upload_url(self, request):
        serializer = DirectUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.create_upload_payload(request.user))

    @action(detail=False, methods=["post"], url_path="complete-direct-upload")
    def complete_direct_upload(self, request):
        serializer = DirectUploadCompleteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document = Document.objects.create(
            owner=request.user,
            subject=data.get("subject"),
            title=data["title"],
            storage_backend=DocumentStorageBackend.R2,
            r2_object_key=data["object_key"],
            original_filename=data["filename"],
            file_size_bytes=data["file_size_bytes"],
            content_type=data.get("content_type") or "application/pdf",
        )
        extract_chapters_from_document.delay(document.id)
        return response.Response(DocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Subject.objects.filter(owner=self.request.user)
            .annotate(document_count=Count("documents"))
            .order_by("name")
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        subject = self.get_object()
        if subject.documents.exists():
            return response.Response(
                {"detail": "Delete or move this subject's textbooks before deleting the subject."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subject_id = subject.id
        subject_name = subject.name
        result = super().destroy(request, *args, **kwargs)
        log_admin_action(
            request=request,
            action="subject_deleted",
            target_type="subject",
            target_id=subject_id,
            description=f"User {request.user.username} deleted subject '{subject_name}'.",
            metadata={"subject_name": subject_name, "owner_id": request.user.id},
        )
        return result


class ChapterConceptListView(generics.ListAPIView):
    serializer_class = ConceptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        subject_id = self.request.query_params.get("subject")
        filters = {
            "chapter_id": self.kwargs["chapter_id"],
            "chapter__document__owner": self.request.user,
        }
        if subject_id:
            filters["chapter__document__subject_id"] = subject_id

        return Concept.objects.filter(
            **filters,
        ).order_by("sequence_number")
