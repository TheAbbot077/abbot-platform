from django.db import transaction
from django.utils import timezone

from documents.models import Chapter, Concept, Document

from .models import (
    ConceptLesson,
    ConceptMastery,
    ConceptProgress,
    ProgressStatus,
    QuizAttempt,
    QuizQuestion,
    ReinforcementRecommendation,
    StudentAIMemory,
    StudentAIReinforcementReport,
    StudentAISpotQuizAttempt,
    TutorMessage,
)
from .services import sync_document_progress


def restart_concept(user, concept: Concept) -> None:
    """Reset one concept without changing chapter/concept sequence numbers."""

    with transaction.atomic():
        _clear_learning_records(user, [concept])
        progress, _created = ConceptProgress.objects.get_or_create(user=user, concept=concept)
        progress.status = ProgressStatus.UNLOCKED
        progress.unlocked_at = timezone.now()
        progress.mastered_at = None
        progress.attempts_count = 0
        progress.last_score = None
        progress.save(
            update_fields=[
                "status",
                "unlocked_at",
                "mastered_at",
                "attempts_count",
                "last_score",
                "updated_at",
            ]
        )

    sync_document_progress(user, concept.chapter.document)


def restart_chapter(user, chapter: Chapter) -> None:
    """Reset all concepts in a chapter while preserving their explicit order."""

    concepts = list(chapter.concepts.order_by("sequence_number"))
    with transaction.atomic():
        _clear_learning_records(user, concepts)
        ConceptProgress.objects.filter(user=user, concept__in=concepts).delete()
        chapter.student_progress.filter(user=user).delete()

    sync_document_progress(user, chapter.document)


def restart_document(user, document: Document) -> None:
    """Reset all progress for a document without deleting the uploaded file."""

    concepts = list(Concept.objects.filter(chapter__document=document).order_by("chapter__sequence_number", "sequence_number"))
    with transaction.atomic():
        _clear_learning_records(user, concepts)
        ConceptProgress.objects.filter(user=user, concept__in=concepts).delete()
        for chapter in document.chapters.all():
            chapter.student_progress.filter(user=user).delete()

    sync_document_progress(user, document)


def _clear_learning_records(user, concepts: list[Concept]) -> None:
    concept_ids = [concept.id for concept in concepts]
    if not concept_ids:
        return

    QuizAttempt.objects.filter(user=user, concept_id__in=concept_ids).delete()
    ConceptMastery.objects.filter(user=user, concept_id__in=concept_ids).delete()
    ConceptLesson.objects.filter(user=user, concept_id__in=concept_ids).delete()
    TutorMessage.objects.filter(user=user, concept_id__in=concept_ids).delete()
    StudentAIMemory.objects.filter(user=user, concept_id__in=concept_ids).delete()
    StudentAISpotQuizAttempt.objects.filter(user=user, concept_id__in=concept_ids).delete()
    ReinforcementRecommendation.objects.filter(user=user, concept_id__in=concept_ids).delete()
    StudentAIReinforcementReport.objects.filter(user=user).delete()

    # QuizQuestion is currently concept-scoped, not user-scoped. Removing these
    # stale generated questions keeps restarted lessons from reusing old MCQs.
    QuizQuestion.objects.filter(concept_id__in=concept_ids).delete()
