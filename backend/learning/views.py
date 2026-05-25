import json

from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from rest_framework import permissions, response, status, views

from core.audit import log_admin_action
from documents.models import Chapter, Concept, Document

from .dashboard import build_progress_dashboard
from .mcq import DEFAULT_MCQ_COUNT, get_or_generate_current_concept_mcqs
from .openai_client import OpenAIServiceError
from .grading import submit_current_concept_answers
from .serializers import (
    ChapterProgressSerializer,
    ConceptProgressSerializer,
    QuizAnswerSubmissionSerializer,
    QuizAttemptResultSerializer,
    QuizQuestionSerializer,
    DashboardSerializer,
    StudentAIAnswerSerializer,
    StudentAIExaminerCheckSerializer,
    StudentAIExaminerResultSerializer,
    StudentAIQuestionSerializer,
    StudentAITeachSerializer,
    StudentAIMemorySerializer,
    TutorAnswerSerializer,
    TutorLessonSerializer,
    TutorQuestionSerializer,
)
from .models import StudentAIMemory
from .ariel_permissions import can_submit_ariel_to_examiner, can_teach_ariel
from .services import get_current_unlocked_concept, get_document_progress
from .restart import restart_chapter, restart_concept, restart_document
from .student_ai import answer_student_ai_question, teach_student_ai_memory
from .spot_quiz import process_student_ai_spot_quiz
from .tutor import answer_current_concept_question, teach_current_unlocked_concept


def _apply_subject_filter(filters: dict, subject_id):
    if subject_id not in (None, ""):
        filters["subject_id"] = subject_id
    return filters


def _apply_concept_subject_filter(filters: dict, subject_id):
    if subject_id not in (None, ""):
        filters["chapter__document__subject_id"] = subject_id
    return filters


def _apply_memory_subject_filter(filters: dict, subject_id):
    if subject_id not in (None, ""):
        filters["concept__chapter__document__subject_id"] = subject_id
    return filters


class CurrentUnlockedConceptView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id: int):
        filters = _apply_subject_filter(
            {"id": document_id, "owner": request.user},
            request.query_params.get("subject"),
        )
        document = get_object_or_404(Document, **filters)
        current = get_current_unlocked_concept(request.user, document)
        if current is None:
            return response.Response({"current_concept": None})

        serializer = ConceptProgressSerializer(current.progress)
        return response.Response({"current_concept": serializer.data})


class ProgressDashboardView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        dashboard = build_progress_dashboard(request.user, subject_id=request.query_params.get("subject"))
        serializer = DashboardSerializer(data=dashboard)
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.data)


class DocumentProgressView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id: int):
        filters = _apply_subject_filter(
            {"id": document_id, "owner": request.user},
            request.query_params.get("subject"),
        )
        document = get_object_or_404(Document, **filters)
        progress_rows = get_document_progress(request.user, document)
        serializer = ChapterProgressSerializer(progress_rows, many=True, context={"request": request})
        return response.Response({"document_id": document.id, "chapters": serializer.data})


class TutorCurrentConceptView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id: int):
        filters = _apply_subject_filter(
            {"id": document_id, "owner": request.user},
            request.query_params.get("subject"),
        )
        document = get_object_or_404(Document, **filters)
        try:
            lesson = teach_current_unlocked_concept(request.user, document)
        except ImproperlyConfigured as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (OpenAIServiceError, json.JSONDecodeError) as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if lesson is None:
            return response.Response({"lesson": None, "next_action": "no_unlocked_concept"})

        serializer = TutorLessonSerializer(data=lesson)
        if not serializer.is_valid():
            return response.Response(
                {
                    "detail": "The Abbot's response did not match the expected lesson format.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return response.Response(serializer.data)


class CurrentConceptMCQView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id: int):
        document = get_object_or_404(Document, id=document_id, owner=request.user)
        question_count = int(request.query_params.get("count", DEFAULT_MCQ_COUNT))
        try:
            questions = get_or_generate_current_concept_mcqs(request.user, document, question_count=question_count)
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ImproperlyConfigured as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (OpenAIServiceError, json.JSONDecodeError, KeyError) as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        serializer = QuizQuestionSerializer(questions, many=True)
        return response.Response({"questions": serializer.data})


class TutorAskView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question_serializer = TutorQuestionSerializer(data=request.data)
        question_serializer.is_valid(raise_exception=True)
        concept_id = question_serializer.validated_data["concept_id"]
        filters = _apply_subject_filter(
            {"chapters__concepts__id": concept_id, "owner": request.user},
            question_serializer.validated_data.get("subject_id"),
        )
        document = get_object_or_404(Document, **filters)

        try:
            answer = answer_current_concept_question(
                request.user,
                document,
                concept_id=concept_id,
                question=question_serializer.validated_data["question"],
            )
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ImproperlyConfigured as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (OpenAIServiceError, json.JSONDecodeError) as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        answer_serializer = TutorAnswerSerializer(data=answer)
        answer_serializer.is_valid(raise_exception=True)
        return response.Response(answer_serializer.data)


class StudentAIMemoryTeachView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        teach_serializer = StudentAITeachSerializer(data=request.data)
        teach_serializer.is_valid(raise_exception=True)
        concept_id = teach_serializer.validated_data["concept_id"]
        filters = _apply_concept_subject_filter(
            {"id": concept_id, "chapter__document__owner": request.user},
            teach_serializer.validated_data.get("subject_id"),
        )
        concept = get_object_or_404(Concept, **filters)
        if not can_teach_ariel(request.user, concept):
            return response.Response(
                {"detail": "Pass this concept before teaching it to Ariel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        memory = teach_student_ai_memory(
            request.user,
            concept,
            taught_content=teach_serializer.validated_data["taught_content"],
            initial_mastery_score=teach_serializer.validated_data["initial_mastery_score"],
        )
        return response.Response(StudentAIMemorySerializer(memory).data, status=status.HTTP_201_CREATED)


class StudentAIAskView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question_serializer = StudentAIQuestionSerializer(data=request.data)
        question_serializer.is_valid(raise_exception=True)
        concept_id = question_serializer.validated_data["concept_id"]
        filters = _apply_concept_subject_filter(
            {"id": concept_id, "chapter__document__owner": request.user},
            question_serializer.validated_data.get("subject_id"),
        )
        concept = get_object_or_404(Concept, **filters)

        try:
            answer = answer_student_ai_question(
                request.user,
                concept,
                question=question_serializer.validated_data["question"],
            )
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ImproperlyConfigured as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (OpenAIServiceError, json.JSONDecodeError) as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        answer_serializer = StudentAIAnswerSerializer(data=answer)
        answer_serializer.is_valid(raise_exception=True)
        return response.Response(answer_serializer.data)


class StudentAIExaminerCheckView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        check_serializer = StudentAIExaminerCheckSerializer(data=request.data)
        check_serializer.is_valid(raise_exception=True)
        concept_id = check_serializer.validated_data["concept_id"]
        filters = _apply_memory_subject_filter(
            {
                "user": request.user,
                "concept_id": concept_id,
                "concept__chapter__document__owner": request.user,
            },
            check_serializer.validated_data.get("subject_id"),
        )
        memory = get_object_or_404(
            StudentAIMemory.objects.select_related("concept", "concept__chapter", "concept__chapter__document"),
            **filters,
        )
        if not can_submit_ariel_to_examiner(request.user, memory.concept.chapter):
            return response.Response(
                {"detail": "Finish this chapter before submitting Ariel to the examiner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            attempt = process_student_ai_spot_quiz(memory)
        except ImproperlyConfigured as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (OpenAIServiceError, json.JSONDecodeError) as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return response.Response(StudentAIExaminerResultSerializer(attempt).data)


class CurrentConceptMCQSubmissionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id: int):
        document = get_object_or_404(Document, id=document_id, owner=request.user)
        submission_serializer = QuizAnswerSubmissionSerializer(data=request.data)
        submission_serializer.is_valid(raise_exception=True)

        try:
            attempt = submit_current_concept_answers(
                request.user,
                document,
                submission_serializer.validated_data["answers"],
            )
        except ValueError as exc:
            return response.Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if attempt is None:
            return response.Response({"detail": "No unlocked concept is available."}, status=status.HTTP_400_BAD_REQUEST)

        result_serializer = QuizAttemptResultSerializer(attempt)
        return response.Response(result_serializer.data)


class RestartCurrentConceptView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id: int):
        document = get_object_or_404(Document, id=document_id, owner=request.user)
        current = get_current_unlocked_concept(request.user, document)
        if current is None:
            return response.Response({"detail": "No current concept is available to restart."}, status=status.HTTP_400_BAD_REQUEST)

        restart_concept(request.user, current.concept)
        log_admin_action(
            request=request,
            action="lesson_restart",
            target_type="concept",
            target_id=current.concept.id,
            description=f"User {request.user.username} restarted concept lesson '{current.concept.title}'.",
            metadata={"document_id": document.id, "concept_title": current.concept.title},
        )
        return response.Response({"detail": "Current concept restarted."})


class RestartChapterView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chapter_id: int):
        chapter = get_object_or_404(Chapter, id=chapter_id, document__owner=request.user)
        restart_chapter(request.user, chapter)
        log_admin_action(
            request=request,
            action="chapter_restart",
            target_type="chapter",
            target_id=chapter.id,
            description=f"User {request.user.username} restarted chapter '{chapter.title}'.",
            metadata={"document_id": chapter.document_id, "chapter_title": chapter.title},
        )
        return response.Response({"detail": "Chapter restarted."})


class RestartDocumentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id: int):
        document = get_object_or_404(Document, id=document_id, owner=request.user)
        restart_document(request.user, document)
        log_admin_action(
            request=request,
            action="textbook_restart",
            target_type="document",
            target_id=document.id,
            description=f"User {request.user.username} restarted textbook '{document.title}'.",
            metadata={"document_title": document.title},
        )
        return response.Response({"detail": "Textbook restarted."})
