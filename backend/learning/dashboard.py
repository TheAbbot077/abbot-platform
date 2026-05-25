from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from documents.models import Document

from .forgetting import calculate_decayed_mastery
from .ariel_permissions import can_submit_ariel_to_examiner
from .models import ConceptMastery, ConceptProgress, ProgressStatus, QuizAttempt, StudentAIMemory
from .reinforcement_service import build_teachback_memory_engine
from .services import get_current_unlocked_concept, sync_document_progress


def build_progress_dashboard(user, subject_id=None) -> dict:
    memory_engine = build_teachback_memory_engine(user, subject_id=subject_id)
    documents = []
    document_queryset = Document.objects.filter(owner=user).select_related("subject").order_by("-created_at")
    if subject_id not in (None, ""):
        document_queryset = document_queryset.filter(subject_id=subject_id)

    include_chapters = subject_id not in (None, "")
    for document in document_queryset:
        sync_document_progress(user, document)
        current = get_current_unlocked_concept(user, document)
        documents.append(_build_document_dashboard(user, document, current, include_chapters=include_chapters))

    return {
        "documents": documents,
        "student_ai_reinforcement": {
            "headline": memory_engine["headline"],
            "recommendations": memory_engine["daily_rescue_missions"],
        },
        "teachback_memory_engine": memory_engine,
    }


def _build_document_dashboard(user, document: Document, current, *, include_chapters: bool) -> dict:
    chapters = []
    document_required_count = 0
    document_passed_count = 0

    for chapter in document.chapters.order_by("sequence_number"):
        if include_chapters:
            chapter_data, required_count, passed_count = _build_chapter_dashboard(user, chapter)
            chapters.append(chapter_data)
        else:
            required_count, passed_count = _chapter_counts(user, chapter)
        document_required_count += required_count
        document_passed_count += passed_count

    current_chapter = current.concept.chapter if current else None
    return {
        "document_id": document.id,
        "subject_id": document.subject_id,
        "subject_name": document.subject.name if document.subject else None,
        "title": document.title,
        "status": document.status,
        "completion_percentage": _percentage(document_passed_count, document_required_count),
        "current_recommended_next_action": _recommended_next_action(current),
        "current_chapter_title": current_chapter.title if current_chapter else None,
        "current_concept_title": current.concept.title if current else None,
        "chapters": chapters,
    }


def _build_chapter_dashboard(user, chapter) -> tuple[dict, int, int]:
    concepts = []
    required_count = 0
    passed_count = 0

    progress_by_concept_id = {
        progress.concept_id: progress
        for progress in ConceptProgress.objects.filter(user=user, concept__chapter=chapter).select_related("concept")
    }
    latest_attempt_by_concept_id = _latest_attempts_by_concept_id(user, chapter)
    mastery_by_concept_id = _mastery_by_concept_id(user, chapter)
    ariel_memory_concept_ids = set(
        StudentAIMemory.objects.filter(user=user, concept__chapter=chapter).values_list("concept_id", flat=True)
    )

    for concept in chapter.concepts.order_by("sequence_number"):
        progress = progress_by_concept_id.get(concept.id)
        latest_attempt = latest_attempt_by_concept_id.get(concept.id)
        mastery = mastery_by_concept_id.get(concept.id)
        status = _dashboard_concept_status(progress, latest_attempt)

        if concept.is_required:
            required_count += 1
            if status == "passed":
                passed_count += 1

        concepts.append(
            {
                "concept_id": concept.id,
                "title": concept.title,
                "sequence_number": concept.sequence_number,
                "is_required": concept.is_required,
                "status": status,
                "last_score": str(progress.last_score) if progress and progress.last_score is not None else None,
                "bloom_level_scores": mastery.bloom_level_scores if mastery else {},
                "mastery_score": str(mastery.mastery_score) if mastery else None,
                "decayed_mastery_score": str(calculate_decayed_mastery(mastery, timezone.now())) if mastery else None,
                "mastery_strength": mastery.mastery_strength if mastery else None,
                "last_reviewed_at": mastery.last_reviewed_at.isoformat() if mastery and mastery.last_reviewed_at else None,
                "next_review_at": mastery.next_review_at.isoformat() if mastery and mastery.next_review_at else None,
                "forgetting_rate": str(mastery.forgetting_rate) if mastery else None,
                "ariel_teachable": status == "passed",
                "ariel_taught": concept.id in ariel_memory_concept_ids,
            }
        )

    return (
        {
            "chapter_id": chapter.id,
            "title": chapter.title,
            "sequence_number": chapter.sequence_number,
            "completion_percentage": _percentage(passed_count, required_count),
            "ariel_teachable_count": sum(1 for concept in concepts if concept["ariel_teachable"]),
            "ariel_examiner_unlocked": can_submit_ariel_to_examiner(user, chapter),
            "concepts": concepts,
        },
        required_count,
        passed_count,
    )


def _chapter_counts(user, chapter) -> tuple[int, int]:
    required_count = 0
    passed_count = 0
    progress_by_concept_id = {
        progress.concept_id: progress
        for progress in ConceptProgress.objects.filter(user=user, concept__chapter=chapter)
    }

    for concept in chapter.concepts.order_by("sequence_number").only("id", "is_required"):
        if not concept.is_required:
            continue
        required_count += 1
        progress = progress_by_concept_id.get(concept.id)
        if progress and progress.status == ProgressStatus.MASTERED:
            passed_count += 1

    return required_count, passed_count


def _latest_attempts_by_concept_id(user, chapter) -> dict[int, QuizAttempt]:
    latest_attempts = {}
    attempts = QuizAttempt.objects.filter(user=user, concept__chapter=chapter).order_by("concept_id", "-created_at")
    for attempt in attempts:
        latest_attempts.setdefault(attempt.concept_id, attempt)
    return latest_attempts


def _mastery_by_concept_id(user, chapter) -> dict[int, ConceptMastery]:
    return {
        mastery.concept_id: mastery
        for mastery in ConceptMastery.objects.filter(user=user, concept__chapter=chapter)
    }


def _dashboard_concept_status(progress: ConceptProgress | None, latest_attempt: QuizAttempt | None) -> str:
    if progress is None:
        return "locked"

    if progress.status == ProgressStatus.MASTERED:
        return "passed"

    if latest_attempt is not None and not latest_attempt.passed:
        return "failed"

    if progress.status == ProgressStatus.UNLOCKED:
        return "available"

    if progress.status == ProgressStatus.IN_PROGRESS:
        return "in_progress"

    return "locked"


def _recommended_next_action(current) -> str:
    if current is None:
        return "document_complete"

    if current.progress.status == ProgressStatus.IN_PROGRESS:
        return "continue_current_concept"

    return "start_current_concept"


def _percentage(passed_count: int, required_count: int) -> str:
    if required_count == 0:
        return "0.00"

    value = Decimal(passed_count) / Decimal(required_count) * Decimal("100")
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
