from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from documents.models import Concept, Document

from .models import ChapterProgress, ConceptProgress, ProgressStatus


@dataclass(frozen=True)
class CurrentConcept:
    concept: Concept
    progress: ConceptProgress


def sync_document_progress(user, document: Document) -> None:
    """Create and update progress rows using chapter/concept sequence only."""

    with transaction.atomic():
        chapters = list(document.chapters.order_by("sequence_number"))
        for chapter in chapters:
            ChapterProgress.objects.get_or_create(user=user, chapter=chapter)

            required_concepts = chapter.concepts.filter(is_required=True).order_by("sequence_number")
            for concept in required_concepts:
                ConceptProgress.objects.get_or_create(user=user, concept=concept)

        _recalculate_unlocks(user, document)


def get_current_unlocked_concept(user, document: Document) -> CurrentConcept | None:
    sync_document_progress(user, document)

    progress = (
        ConceptProgress.objects.select_related("concept", "concept__chapter")
        .filter(
            user=user,
            concept__chapter__document=document,
            concept__is_required=True,
            status__in=[ProgressStatus.UNLOCKED, ProgressStatus.IN_PROGRESS],
        )
        .order_by("concept__chapter__sequence_number", "concept__sequence_number")
        .first()
    )
    if progress is None:
        return None

    return CurrentConcept(concept=progress.concept, progress=progress)


def mark_concept_mastered(user, concept: Concept) -> None:
    """Mark a concept passed, then unlock the next eligible item."""

    now = timezone.now()
    progress, _created = ConceptProgress.objects.get_or_create(user=user, concept=concept)
    progress.status = ProgressStatus.MASTERED
    progress.mastered_at = now
    progress.save(update_fields=["status", "mastered_at", "updated_at"])

    sync_document_progress(user, concept.chapter.document)


def get_document_progress(user, document: Document) -> list[ChapterProgress]:
    sync_document_progress(user, document)
    return list(
        ChapterProgress.objects.filter(user=user, chapter__document=document)
        .select_related("chapter")
        .prefetch_related("chapter__concepts")
        .order_by("chapter__sequence_number")
    )


def _recalculate_unlocks(user, document: Document) -> None:
    now = timezone.now()
    previous_chapter_is_complete = True

    for chapter in document.chapters.order_by("sequence_number"):
        chapter_progress = ChapterProgress.objects.get(user=user, chapter=chapter)
        required_concepts = list(chapter.concepts.filter(is_required=True).order_by("sequence_number"))

        if not previous_chapter_is_complete:
            _lock_unmastered_chapter(user, chapter_progress, required_concepts)
            continue

        if chapter_progress.status == ProgressStatus.LOCKED:
            chapter_progress.status = ProgressStatus.UNLOCKED
            chapter_progress.unlocked_at = now
            chapter_progress.save(update_fields=["status", "unlocked_at", "updated_at"])

        chapter_is_complete = _unlock_next_required_concept(user, required_concepts, now)
        if chapter_is_complete and chapter_progress.status != ProgressStatus.MASTERED:
            chapter_progress.status = ProgressStatus.MASTERED
            chapter_progress.mastered_at = now
            chapter_progress.save(update_fields=["status", "mastered_at", "updated_at"])
        elif not chapter_is_complete and chapter_progress.status == ProgressStatus.MASTERED:
            chapter_progress.status = ProgressStatus.UNLOCKED
            chapter_progress.mastered_at = None
            chapter_progress.save(update_fields=["status", "mastered_at", "updated_at"])

        previous_chapter_is_complete = chapter_is_complete


def _unlock_next_required_concept(user, required_concepts: list[Concept], now) -> bool:
    all_required_concepts_mastered = True

    for concept in required_concepts:
        progress = ConceptProgress.objects.get(user=user, concept=concept)
        if progress.status == ProgressStatus.MASTERED:
            continue

        all_required_concepts_mastered = False
        if progress.status == ProgressStatus.LOCKED:
            progress.status = ProgressStatus.UNLOCKED
            progress.unlocked_at = now
            progress.save(update_fields=["status", "unlocked_at", "updated_at"])
        break

    return all_required_concepts_mastered


def _lock_unmastered_chapter(user, chapter_progress: ChapterProgress, required_concepts: list[Concept]) -> None:
    if chapter_progress.status != ProgressStatus.LOCKED:
        chapter_progress.status = ProgressStatus.LOCKED
        chapter_progress.mastered_at = None
        chapter_progress.save(update_fields=["status", "mastered_at", "updated_at"])

    for concept in required_concepts:
        progress = ConceptProgress.objects.get(user=user, concept=concept)
        if progress.status != ProgressStatus.LOCKED:
            progress.status = ProgressStatus.LOCKED
            progress.mastered_at = None
            progress.save(update_fields=["status", "mastered_at", "updated_at"])
