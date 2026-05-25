import logging
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, response, status, views

from documents.deletion import delete_document_tree
from documents.models import Chapter, Concept, Document, DocumentStatus, Subject
from documents.parsing.chapter_detector import (
    detect_ordered_chapters_with_metadata,
    fallback_single_chapter_candidate,
    multiline_heading_candidates,
    regex_heading_candidates,
    toc_like_candidates,
)
from documents.parsing.chapter_sequence_resolver import select_best_chapter_sequence
from documents.parsing.pdf_text_extractor import extract_text_from_pdf
from documents.tasks import extract_chapters_from_document
from learning.models import (
    ChapterProgress,
    ConceptLesson,
    ConceptMastery,
    ConceptProgress,
    ProgressStatus,
    QuizAttempt,
    QuizQuestion,
    ReinforcementRecommendation,
    StudentAIMemory,
    StudentAISpotQuizAttempt,
    TutorMessage,
)

from .audit import log_admin_action
from .models import AdminAuditLog
from .permissions import CanManageQualityTools, CanManageTextbooks, CanManageUsers, CanViewAuditLogs, IsStaffUser
from .serializers import (
    AdminAuditLogListSerializer,
    AdminConceptQualityListSerializer,
    AdminParserPreviewSerializer,
    AdminTextbookDetailSerializer,
    AdminTextbookListSerializer,
    AdminUserDetailSerializer,
    AdminUserListSerializer,
    AdminUserAnalyticsSerializer,
    CommandCenterDashboardSerializer,
)


LOW_CONFIDENCE_THRESHOLD = 0.7
RECENT_LIMIT = 8
USER_LIST_LIMIT = 50
TEXTBOOK_LIST_LIMIT = 75
QUALITY_CONCEPT_LIST_LIMIT = 100
AUDIT_LOG_LIST_LIMIT = 100
logger = logging.getLogger(__name__)


class HealthCheckView(views.APIView):
    """Small public endpoint for platform health checks."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return response.Response({"status": "ok"})


class CommandCenterDashboardView(views.APIView):
    """Administrative product overview for staff users only."""

    permission_classes = [IsStaffUser]

    def get(self, request):
        payload = {
            "title": "Abbot Command Center",
            "metrics": _command_center_metrics(),
            "recent_uploaded_textbooks": _recent_uploaded_textbooks(),
            "recent_failed_jobs": _recent_failed_jobs(),
        }
        serializer = CommandCenterDashboardSerializer(payload)
        return response.Response(serializer.data)


class AdminUserAnalyticsView(views.APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        return response.Response(AdminUserAnalyticsSerializer(_userbase_analytics()).data)


class AdminUserListView(views.APIView):
    permission_classes = [CanManageUsers]

    def get(self, request):
        users = _filtered_users(request).annotate(
            subject_count=Count("subjects", distinct=True),
            document_count=Count("documents", distinct=True),
            quiz_attempt_count=Count("quiz_attempts", distinct=True),
        )
        total_count = users.count()
        payload = {
            "users": [_user_list_item(user) for user in users.order_by("-date_joined")[:USER_LIST_LIMIT]],
            "total_count": total_count,
        }
        return response.Response(AdminUserListSerializer(payload).data)


class AdminUserDetailView(views.APIView):
    permission_classes = [CanManageUsers]

    def get(self, request, user_id: int):
        user = get_object_or_404(get_user_model(), id=user_id)
        return response.Response(AdminUserDetailSerializer(_user_detail(user)).data)


class AdminUserActivationView(views.APIView):
    permission_classes = [CanManageUsers]

    def post(self, request, user_id: int, action: str):
        user = get_object_or_404(get_user_model(), id=user_id)
        if user.id == request.user.id and action == "deactivate":
            return response.Response(
                {"detail": "Administrators cannot deactivate their own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "deactivate":
            user.is_active = False
        elif action == "reactivate":
            user.is_active = True
        else:
            return response.Response({"detail": "Unsupported user action."}, status=status.HTTP_404_NOT_FOUND)

        user.save(update_fields=["is_active"])
        log_admin_action(
            request=request,
            action=f"user_{action}",
            target_type="user",
            target_id=user.id,
            description=f"Admin {request.user.username} {action}d user {user.username}.",
            metadata={"target_username": user.username, "target_email": user.email},
        )
        logger.info(
            "Admin user %s %sd account %s",
            request.user.id,
            action,
            user.id,
        )
        return response.Response(AdminUserDetailSerializer(_user_detail(user)).data)


class AdminTextbookListView(views.APIView):
    permission_classes = [CanManageTextbooks]

    def get(self, request):
        textbooks = _filtered_textbooks(request).annotate(
            chapter_count=Count("chapters", distinct=True),
            concept_count=Count("chapters__concepts", distinct=True),
        )
        total_count = textbooks.count()
        payload = {
            "textbooks": [_textbook_summary(textbook) for textbook in textbooks.order_by("-created_at")[:TEXTBOOK_LIST_LIMIT]],
            "total_count": total_count,
        }
        return response.Response(AdminTextbookListSerializer(payload).data)


class AdminTextbookDetailView(views.APIView):
    permission_classes = [CanManageTextbooks]

    def get(self, request, document_id: int):
        document = _admin_document(document_id)
        return response.Response(AdminTextbookDetailSerializer(_textbook_detail(document)).data)

    def delete(self, request, document_id: int):
        document = _admin_document(document_id)
        if str(request.query_params.get("confirm", "")).lower() != "true":
            return response.Response(
                {"detail": "Deletion requires confirm=true because it cascades chapters, concepts, progress, and stored file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        title = document.title
        owner_id = document.owner_id
        delete_document_tree(document)
        log_admin_action(
            request=request,
            action="textbook_deleted",
            target_type="document",
            target_id=document_id,
            description=f"Admin {request.user.username} deleted textbook '{title}'.",
            metadata={"title": title, "owner_id": owner_id},
        )
        logger.info("Admin user %s deleted textbook %s (%s)", request.user.id, document_id, title)
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class AdminTextbookParserPreviewView(views.APIView):
    permission_classes = [CanManageTextbooks]

    def get(self, request, document_id: int):
        document = _admin_document(document_id)
        document_text = extract_text_from_pdf(document.file.path)
        legacy_result = detect_ordered_chapters_with_metadata(document_text)
        resolver_result = select_best_chapter_sequence(_chapter_candidates(document_text), full_text=document_text)
        stored_chapters = list(document.chapters.order_by("sequence_number").annotate(concept_count=Count("concepts")))
        payload = {
            "document_id": document.id,
            "title": document.title,
            "current_stored_chapters": [_chapter_summary(chapter) for chapter in stored_chapters],
            "legacy": _parser_result_summary(legacy_result),
            "resolver": _parser_result_summary(resolver_result),
            "differences": _stored_vs_proposed_differences(stored_chapters, legacy_result.accepted_chapters),
            "progress_summary": _progress_summary(document),
            "progress_exists": _has_progress(_progress_summary(document)),
        }
        return response.Response(AdminParserPreviewSerializer(payload).data)


class AdminTextbookReprocessView(views.APIView):
    permission_classes = [CanManageTextbooks]

    def post(self, request, document_id: int):
        document = _admin_document(document_id)
        if request.data.get("confirm") is not True:
            return response.Response(
                {"detail": "Reprocessing requires confirm=true after reviewing parser preview."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        progress_summary = _progress_summary(document)
        if _has_progress(progress_summary) and request.data.get("force_reset_progress") is not True:
            return response.Response(
                {
                    "detail": (
                        "Learning progress exists for this textbook. Reprocessing may reset chapters, concepts, "
                        "quizzes, lessons, Ariel memory, and recommendations."
                    ),
                    "progress_summary": progress_summary,
                    "requires_force_reset_progress": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        extract_chapters_from_document.delay(document.id)
        log_admin_action(
            request=request,
            action="textbook_reprocess_queued",
            target_type="document",
            target_id=document.id,
            description=f"Admin {request.user.username} queued textbook reprocessing for '{document.title}'.",
            metadata={
                "title": document.title,
                "force_reset_progress": request.data.get("force_reset_progress") is True,
                "progress_summary": progress_summary,
            },
        )
        logger.info("Admin user %s queued textbook reprocess for document %s", request.user.id, document.id)
        return response.Response(
            {
                "detail": "Textbook reprocessing has been queued.",
                "document_id": document.id,
                "progress_summary": progress_summary,
                "progress_reset_confirmed": _has_progress(progress_summary),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AdminConceptQualityListView(views.APIView):
    permission_classes = [CanManageQualityTools]

    def get(self, request):
        concepts = _filtered_quality_concepts(request).annotate(
            question_count=Count("quiz_questions", distinct=True),
            unanswered_question_count=Count(
                "quiz_questions",
                filter=Q(quiz_questions__is_answered=False),
                distinct=True,
            ),
            quiz_attempt_count=Count("quiz_attempts", distinct=True),
            pass_count=Count("quiz_attempts", filter=Q(quiz_attempts__passed=True), distinct=True),
            fail_count=Count("quiz_attempts", filter=Q(quiz_attempts__passed=False), distinct=True),
            lesson_count=Count("lessons", distinct=True),
            tutor_message_count=Count("tutor_messages", distinct=True),
        )
        concept_rows = [_concept_quality_summary(concept) for concept in concepts.order_by(
            "chapter__document__title",
            "chapter__sequence_number",
            "sequence_number",
        )[:QUALITY_CONCEPT_LIST_LIMIT]]

        issue_filter = request.query_params.get("issue", "all")
        if issue_filter == "objective":
            concept_rows = [row for row in concept_rows if row["possible_objective_match"]]
        elif issue_filter == "failed":
            concept_rows = [row for row in concept_rows if row["fail_count"] > 0]

        payload = {
            "concepts": concept_rows,
            "total_count": concepts.count(),
            "commonly_failed_concepts": _commonly_failed_concepts(),
            "flagged_questions": _flagged_questions_summary(),
        }
        return response.Response(AdminConceptQualityListSerializer(payload).data)


class AdminConceptRegenerateMcqsView(views.APIView):
    permission_classes = [CanManageQualityTools]

    def post(self, request, concept_id: int):
        concept = get_object_or_404(Concept, id=concept_id)
        if request.data.get("confirm") is not True:
            return response.Response(
                {"detail": "Refreshing MCQs requires confirm=true. Only unanswered generated questions are removed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = QuizQuestion.objects.filter(concept=concept, is_answered=False).delete()
        log_admin_action(
            request=request,
            action="mcq_regenerated",
            target_type="concept",
            target_id=concept.id,
            description=f"Admin {request.user.username} cleared unanswered MCQs for '{concept.title}'.",
            metadata={"concept_title": concept.title, "deleted_count": deleted_count},
        )
        logger.info("Admin user %s refreshed unanswered MCQs for concept %s", request.user.id, concept.id)
        return response.Response(
            {
                "detail": "Unanswered MCQs were cleared. The next student quiz request will generate fresh questions.",
                "concept_id": concept.id,
                "deleted_count": deleted_count,
            }
        )


class AdminConceptRegenerateTutorView(views.APIView):
    permission_classes = [CanManageQualityTools]

    def post(self, request, concept_id: int):
        concept = get_object_or_404(Concept, id=concept_id)
        if request.data.get("confirm") is not True:
            return response.Response(
                {"detail": "Refreshing The Abbot lesson requires confirm=true. Student progress is preserved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = ConceptLesson.objects.filter(concept=concept).delete()
        preserved_messages = TutorMessage.objects.filter(concept=concept).count()
        log_admin_action(
            request=request,
            action="tutor_lesson_regenerated",
            target_type="concept",
            target_id=concept.id,
            description=f"Admin {request.user.username} cleared stored The Abbot lessons for '{concept.title}'.",
            metadata={
                "concept_title": concept.title,
                "deleted_count": deleted_count,
                "tutor_messages_preserved": preserved_messages,
            },
        )
        logger.info("Admin user %s refreshed The Abbot lessons for concept %s", request.user.id, concept.id)
        return response.Response(
            {
                "detail": "Stored The Abbot lessons were cleared. They will regenerate through the normal lesson flow.",
                "concept_id": concept.id,
                "deleted_count": deleted_count,
                "tutor_messages_preserved": preserved_messages,
            }
        )


class AdminAuditLogListView(views.APIView):
    permission_classes = [CanViewAuditLogs]

    def get(self, request):
        logs = _filtered_audit_logs(request)
        payload = {
            "logs": [_audit_log_summary(log) for log in logs.order_by("-created_at")[:AUDIT_LOG_LIST_LIMIT]],
            "total_count": logs.count(),
        }
        return response.Response(AdminAuditLogListSerializer(payload).data)


def _command_center_metrics() -> list[dict]:
    return [
        {"key": "total_users", "label": "Total users", "value": get_user_model().objects.count()},
        {"key": "total_subjects", "label": "Total subjects", "value": Subject.objects.count()},
        {"key": "total_documents", "label": "Total textbooks", "value": Document.objects.count()},
        {"key": "total_chapters", "label": "Total chapters", "value": Chapter.objects.count()},
        {"key": "total_concepts", "label": "Total concepts", "value": Concept.objects.count()},
        {"key": "total_quiz_attempts", "label": "Total quiz attempts", "value": QuizAttempt.objects.count()},
        {"key": "total_tutor_sessions", "label": "Total The Abbot lessons", "value": ConceptLesson.objects.count()},
        {
            "key": "failed_document_processing_count",
            "label": "Failed textbook prep",
            "value": Document.objects.filter(status=DocumentStatus.FAILED).count(),
        },
        {
            "key": "low_confidence_parser_count",
            "label": "Low-confidence parses",
            "value": Document.objects.filter(parser_confidence_score__lt=LOW_CONFIDENCE_THRESHOLD).count(),
        },
    ]


def _userbase_analytics() -> dict:
    now = timezone.now()
    today = now.date()
    user_count = get_user_model().objects.count()
    completed_concepts = ConceptProgress.objects.filter(status=ProgressStatus.MASTERED).count()

    return {
        "total_users": user_count,
        "currently_active_users": get_user_model().objects.filter(profile__last_active_at__gte=now - timedelta(minutes=15)).count(),
        "users_logged_in_today": get_user_model().objects.filter(profile__last_login_at__date=today).count(),
        "daily_active_users": get_user_model().objects.filter(profile__last_active_at__date=today).count(),
        "weekly_active_users": get_user_model().objects.filter(profile__last_active_at__gte=now - timedelta(days=7)).count(),
        "monthly_active_users": get_user_model().objects.filter(profile__last_active_at__gte=now - timedelta(days=30)).count(),
        "users_by_country": _profile_bucket("country", limit=12),
        "users_by_age_range": _profile_bucket("age_range", limit=12),
        "users_by_gender": _profile_bucket("gender", limit=12),
        "users_by_education_level": _profile_bucket("education_level", limit=12),
        "users_by_role": _profile_bucket("role", limit=12),
        "new_signups_over_time": _signup_trend(),
        "textbook_uploads_over_time": _textbook_upload_trend(),
        "concept_completions_over_time": _concept_completion_trend(),
        "quiz_pass_fail_trends": _quiz_pass_fail_trend(),
        "most_active_subjects": _most_active_subjects(),
        "average_textbooks_per_user": round(Document.objects.count() / user_count, 2) if user_count else 0,
        "average_concepts_completed_per_user": round(completed_concepts / user_count, 2) if user_count else 0,
        "privacy_note": (
            "Analytics are aggregated by default. Demographic profile fields are stored separately from auth "
            "credentials and should not be used to expose unnecessary personal details."
        ),
    }


def _profile_bucket(field: str, limit: int = 10) -> list[dict]:
    # Privacy boundary: this returns grouped counts only, not individual user
    # demographics. Superuser-only personal inspection can be added later if a
    # clear operational need exists.
    rows = (
        get_user_model()
        .objects.exclude(**{f"profile__{field}": ""})
        .values(f"profile__{field}")
        .annotate(value=Count("id"))
        .order_by("-value", f"profile__{field}")[:limit]
    )
    return [{"label": row[f"profile__{field}"] or "not_provided", "value": row["value"]} for row in rows]


def _signup_trend(days: int = 14) -> list[dict]:
    start = timezone.now() - timedelta(days=days - 1)
    rows = (
        get_user_model()
        .objects.filter(date_joined__date__gte=start.date())
        .annotate(signup_day=TruncDate("date_joined"))
        .values("signup_day")
        .annotate(signups=Count("id"))
        .order_by("signup_day")
    )
    return [{"date": row["signup_day"], "signups": row["signups"]} for row in rows]


def _textbook_upload_trend(days: int = 14) -> list[dict]:
    start = timezone.now() - timedelta(days=days - 1)
    rows = (
        Document.objects.filter(created_at__date__gte=start.date())
        .annotate(upload_day=TruncDate("created_at"))
        .values("upload_day")
        .annotate(uploads=Count("id"))
        .order_by("upload_day")
    )
    return [{"date": row["upload_day"], "uploads": row["uploads"]} for row in rows]


def _concept_completion_trend(days: int = 14) -> list[dict]:
    start = timezone.now() - timedelta(days=days - 1)
    rows = (
        ConceptProgress.objects.filter(status=ProgressStatus.MASTERED, mastered_at__date__gte=start.date())
        .annotate(completion_day=TruncDate("mastered_at"))
        .values("completion_day")
        .annotate(completions=Count("id"))
        .order_by("completion_day")
    )
    return [{"date": row["completion_day"], "completions": row["completions"]} for row in rows]


def _quiz_pass_fail_trend(days: int = 14) -> list[dict]:
    start = timezone.now() - timedelta(days=days - 1)
    rows = (
        QuizAttempt.objects.filter(created_at__date__gte=start.date())
        .annotate(quiz_day=TruncDate("created_at"))
        .values("quiz_day")
        .annotate(
            pass_count=Count("id", filter=Q(passed=True)),
            fail_count=Count("id", filter=Q(passed=False)),
            total=Count("id"),
        )
        .order_by("quiz_day")
    )
    return [
        {
            "date": row["quiz_day"],
            "passed": row["pass_count"],
            "failed": row["fail_count"],
            "total": row["total"],
        }
        for row in rows
    ]


def _most_active_subjects(limit: int = 8) -> list[dict]:
    rows = (
        Subject.objects.annotate(activity_count=Count("documents__chapters__concepts__quiz_attempts"))
        .filter(activity_count__gt=0)
        .order_by("-activity_count", "name")[:limit]
    )
    return [{"label": subject.name, "value": subject.activity_count} for subject in rows]


def _recent_uploaded_textbooks() -> list[dict]:
    documents = (
        Document.objects.select_related("owner", "subject")
        .order_by("-created_at")[:RECENT_LIMIT]
    )
    return [_document_summary(document) for document in documents]


def _recent_failed_jobs() -> list[dict]:
    documents = (
        Document.objects.select_related("owner")
        .filter(status=DocumentStatus.FAILED)
        .order_by("-updated_at")[:RECENT_LIMIT]
    )
    return [
        {
            "document_id": document.id,
            "title": document.title,
            "owner_username": document.owner.username,
            "status": document.status,
            "parser_warnings": [str(warning) for warning in (document.parser_warnings or [])],
            "updated_at": document.updated_at,
        }
        for document in documents
    ]


def _document_summary(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "owner_username": document.owner.username,
        "subject_name": document.subject.name if document.subject else None,
        "status": document.status,
        "parser_confidence_score": document.parser_confidence_score,
        "parser_strategy": document.parser_strategy,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _filtered_users(request):
    users = get_user_model().objects.all()
    query = request.query_params.get("q", "").strip()
    status_filter = request.query_params.get("status", "all")
    role_filter = request.query_params.get("role", "all")

    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    if role_filter == "staff":
        users = users.filter(is_staff=True)
    elif role_filter == "inactive_staff":
        users = users.filter(is_staff=True, is_active=False)
    elif role_filter == "non_staff":
        users = users.filter(is_staff=False)
    elif role_filter == "superuser":
        users = users.filter(is_superuser=True)

    return users


def _user_list_item(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "date_joined": user.date_joined,
        "last_login": user.last_login,
        "subject_count": getattr(user, "subject_count", 0),
        "document_count": getattr(user, "document_count", 0),
        "quiz_attempt_count": getattr(user, "quiz_attempt_count", 0),
    }


def _user_detail(user) -> dict:
    subjects = (
        Subject.objects.filter(owner=user)
        .annotate(document_count=Count("documents"))
        .order_by("name")
    )
    documents = Document.objects.filter(owner=user).select_related("subject").order_by("-created_at")[:20]
    progress_counts = _progress_counts(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "date_joined": user.date_joined,
        "last_login": user.last_login,
        "summary": {
            "subject_count": subjects.count(),
            "document_count": Document.objects.filter(owner=user).count(),
            "ready_document_count": Document.objects.filter(owner=user, status=DocumentStatus.READY).count(),
            "failed_document_count": Document.objects.filter(owner=user, status=DocumentStatus.FAILED).count(),
            "quiz_attempt_count": QuizAttempt.objects.filter(user=user).count(),
            "tutor_session_count": ConceptLesson.objects.filter(user=user).count(),
        },
        "subjects": [
            {
                "id": subject.id,
                "name": subject.name,
                "document_count": subject.document_count,
            }
            for subject in subjects
        ],
        "textbooks": [
            {
                "id": document.id,
                "title": document.title,
                "subject_name": document.subject.name if document.subject else None,
                "status": document.status,
                "parser_confidence_score": document.parser_confidence_score,
                "created_at": document.created_at,
            }
            for document in documents
        ],
        "learning_progress": progress_counts,
    }


def _progress_counts(user) -> dict:
    progress = ConceptProgress.objects.filter(user=user)
    return {
        "total_progress_records": progress.count(),
        "locked": progress.filter(status=ProgressStatus.LOCKED).count(),
        "available": progress.filter(status=ProgressStatus.UNLOCKED).count(),
        "in_progress": progress.filter(status=ProgressStatus.IN_PROGRESS).count(),
        "passed": progress.filter(status=ProgressStatus.MASTERED).count(),
        "failed": progress.filter(last_score__isnull=False).exclude(status=ProgressStatus.MASTERED).count(),
        "quiz_attempts": QuizAttempt.objects.filter(user=user).count(),
        "tutor_sessions": ConceptLesson.objects.filter(user=user).count(),
    }


def _filtered_textbooks(request):
    textbooks = Document.objects.select_related("owner", "subject").all()
    query = request.query_params.get("q", "").strip()
    status_filter = request.query_params.get("status", "all")
    confidence_filter = request.query_params.get("confidence", "all")

    if query:
        textbooks = textbooks.filter(Q(title__icontains=query) | Q(owner__username__icontains=query))
    if status_filter != "all":
        textbooks = textbooks.filter(status=status_filter)
    if confidence_filter == "low":
        textbooks = textbooks.filter(parser_confidence_score__lt=LOW_CONFIDENCE_THRESHOLD)
    elif confidence_filter == "high":
        textbooks = textbooks.filter(parser_confidence_score__gte=LOW_CONFIDENCE_THRESHOLD)
    elif confidence_filter == "unknown":
        textbooks = textbooks.filter(parser_confidence_score__isnull=True)

    return textbooks


def _filtered_quality_concepts(request):
    concepts = Concept.objects.select_related("chapter", "chapter__document", "chapter__document__owner").all()
    query = request.query_params.get("q", "").strip()
    document_id = request.query_params.get("document_id", "").strip()
    chapter_id = request.query_params.get("chapter_id", "").strip()

    if query:
        concepts = concepts.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(chapter__title__icontains=query)
            | Q(chapter__document__title__icontains=query)
        )
    if document_id.isdigit():
        concepts = concepts.filter(chapter__document_id=int(document_id))
    if chapter_id.isdigit():
        concepts = concepts.filter(chapter_id=int(chapter_id))

    return concepts


def _filtered_audit_logs(request):
    logs = AdminAuditLog.objects.select_related("admin_user").all()
    query = request.query_params.get("q", "").strip()
    action = request.query_params.get("action", "").strip()
    target_type = request.query_params.get("target_type", "").strip()

    if query:
        logs = logs.filter(
            Q(description__icontains=query)
            | Q(action__icontains=query)
            | Q(target_type__icontains=query)
            | Q(target_id__icontains=query)
            | Q(admin_user__username__icontains=query)
        )
    if action:
        logs = logs.filter(action=action)
    if target_type:
        logs = logs.filter(target_type=target_type)

    return logs


def _audit_log_summary(log: AdminAuditLog) -> dict:
    return {
        "id": log.id,
        "admin_user_id": log.admin_user_id,
        "admin_username": log.admin_user.username if log.admin_user else None,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "description": log.description,
        "metadata": log.metadata or {},
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


def _concept_quality_summary(concept: Concept) -> dict:
    pass_count = getattr(concept, "pass_count", 0)
    fail_count = getattr(concept, "fail_count", 0)
    attempt_count = getattr(concept, "quiz_attempt_count", 0)
    objective_match = _matching_chapter_objective(concept)
    return {
        "id": concept.id,
        "title": concept.title,
        "sequence_number": concept.sequence_number,
        "chapter_id": concept.chapter_id,
        "chapter_title": concept.chapter.title,
        "chapter_sequence_number": concept.chapter.sequence_number,
        "document_id": concept.chapter.document_id,
        "document_title": concept.chapter.document.title,
        "owner_username": concept.chapter.document.owner.username,
        "question_count": getattr(concept, "question_count", 0),
        "unanswered_question_count": getattr(concept, "unanswered_question_count", 0),
        "quiz_attempt_count": attempt_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round((pass_count / attempt_count) * 100, 1) if attempt_count else None,
        "lesson_count": getattr(concept, "lesson_count", 0),
        "tutor_message_count": getattr(concept, "tutor_message_count", 0),
        "possible_objective_match": objective_match is not None,
        "matched_objective": objective_match,
    }


def _matching_chapter_objective(concept: Concept) -> str | None:
    title = _normalize_quality_text(concept.title)
    if len(title) < 8:
        return None

    # Objectives are chapter metadata, not teachable concept rows. This heuristic
    # helps admins spot extraction mistakes without changing the learning flow.
    for objective in concept.chapter.chapter_objectives or []:
        objective_text = str(objective)
        normalized_objective = _normalize_quality_text(objective_text)
        if not normalized_objective:
            continue
        if title == normalized_objective or (len(title) >= 12 and title in normalized_objective):
            return objective_text
    return None


def _normalize_quality_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", value.lower())).strip()


def _commonly_failed_concepts() -> list[dict]:
    concepts = (
        Concept.objects.select_related("chapter", "chapter__document")
        .annotate(
            quiz_attempt_count=Count("quiz_attempts", distinct=True),
            pass_count=Count("quiz_attempts", filter=Q(quiz_attempts__passed=True), distinct=True),
            fail_count=Count("quiz_attempts", filter=Q(quiz_attempts__passed=False), distinct=True),
        )
        .filter(fail_count__gt=0)
        .order_by("-fail_count", "chapter__document__title", "chapter__sequence_number", "sequence_number")[:8]
    )
    rows = []
    for concept in concepts:
        attempt_count = getattr(concept, "quiz_attempt_count", 0)
        pass_count = getattr(concept, "pass_count", 0)
        rows.append(
            {
                "id": concept.id,
                "title": concept.title,
                "chapter_title": concept.chapter.title,
                "document_title": concept.chapter.document.title,
                "fail_count": getattr(concept, "fail_count", 0),
                "pass_rate": round((pass_count / attempt_count) * 100, 1) if attempt_count else None,
            }
        )
    return rows


def _flagged_questions_summary() -> dict:
    return {
        "flagging_available": False,
        "total_count": 0,
        "questions": [],
        "message": "Question flagging is not enabled yet. No flagged MCQs are available to review.",
    }


def _admin_document(document_id: int) -> Document:
    return get_object_or_404(
        Document.objects.select_related("owner", "subject").prefetch_related("chapters__concepts"),
        id=document_id,
    )


def _textbook_summary(document: Document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "owner_username": document.owner.username,
        "subject_name": document.subject.name if document.subject else None,
        "status": document.status,
        "parser_confidence_score": document.parser_confidence_score,
        "parser_strategy": document.parser_strategy,
        "parser_warnings": [str(warning) for warning in (document.parser_warnings or [])],
        "chapter_count": getattr(document, "chapter_count", document.chapters.count()),
        "concept_count": getattr(document, "concept_count", Concept.objects.filter(chapter__document=document).count()),
        "progress_exists": _has_progress(_progress_summary(document)),
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _textbook_detail(document: Document) -> dict:
    chapters = document.chapters.annotate(concept_count=Count("concepts")).order_by("sequence_number")
    summary = _textbook_summary(document)
    summary["chapters"] = [_chapter_summary(chapter) for chapter in chapters]
    summary["progress_summary"] = _progress_summary(document)
    return summary


def _chapter_summary(chapter: Chapter) -> dict:
    return {
        "id": chapter.id,
        "title": chapter.title,
        "sequence_number": chapter.sequence_number,
        "concept_count": getattr(chapter, "concept_count", chapter.concepts.count()),
        "created_at": chapter.created_at,
    }


def _progress_summary(document: Document) -> dict[str, int]:
    concept_filter = {"concept__chapter__document": document}
    return {
        "chapter_progress": ChapterProgress.objects.filter(chapter__document=document).count(),
        "concept_progress": ConceptProgress.objects.filter(**concept_filter).count(),
        "quiz_attempts": QuizAttempt.objects.filter(**concept_filter).count(),
        "concept_lessons": ConceptLesson.objects.filter(**concept_filter).count(),
        "tutor_messages": TutorMessage.objects.filter(**concept_filter).count(),
        "concept_mastery": ConceptMastery.objects.filter(**concept_filter).count(),
        "ariel_memory": StudentAIMemory.objects.filter(**concept_filter).count(),
        "ariel_spot_quizzes": StudentAISpotQuizAttempt.objects.filter(**concept_filter).count(),
        "reinforcement_recommendations": ReinforcementRecommendation.objects.filter(**concept_filter).count(),
    }


def _has_progress(progress_summary: dict[str, int]) -> bool:
    return any(count > 0 for count in progress_summary.values())


def _chapter_candidates(text: str):
    candidates = regex_heading_candidates(text)
    candidates.extend(multiline_heading_candidates(text))
    candidates.extend(toc_like_candidates(text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(text))
    return candidates


def _parser_result_summary(result) -> dict:
    return {
        "strategy_used": result.strategy_used,
        "confidence_score": result.confidence_score,
        "warnings": result.warnings,
        "accepted_chapter_count": len(result.accepted_chapters),
        "accepted_chapters": [
            {
                "sequence_number": chapter.sequence_number,
                "title": chapter.title,
                "confidence_score": chapter.confidence_score,
                "detection_methods": chapter.detection_methods,
                "preview": chapter.extracted_text[:300],
            }
            for chapter in result.accepted_chapters
        ],
    }


def _stored_vs_proposed_differences(stored_chapters, proposed_chapters) -> list[str]:
    differences = []
    if len(stored_chapters) != len(proposed_chapters):
        differences.append(f"chapter count differs: stored={len(stored_chapters)}, proposed={len(proposed_chapters)}")

    max_length = max(len(stored_chapters), len(proposed_chapters))
    for index in range(max_length):
        stored_title = stored_chapters[index].title if index < len(stored_chapters) else "<missing>"
        proposed_title = proposed_chapters[index].title if index < len(proposed_chapters) else "<missing>"
        if stored_title != proposed_title:
            differences.append(f"chapter {index + 1}: stored='{stored_title}' proposed='{proposed_title}'")

    return differences
