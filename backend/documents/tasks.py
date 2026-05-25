from celery import shared_task
from dataclasses import replace
from django.conf import settings
from django.db import transaction

from .models import Chapter, Concept, Document, DocumentStatus
from .services import (
    classify_document_content,
    detect_ordered_chapters_with_metadata,
    extract_chapter_learning_content,
    extract_text_from_pdf,
    fallback_single_chapter_candidate,
    multiline_heading_candidates,
    regex_heading_candidates,
    select_best_chapter_sequence,
    toc_like_candidates,
)


@shared_task(bind=True, autoretry_for=(OSError,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def extract_chapters_from_document(self, document_id: int) -> int:
    """Extract and store document chapters using explicit sequence numbers."""

    document = Document.objects.get(id=document_id)
    document.status = DocumentStatus.EXTRACTING_TEXT
    document.save(update_fields=["status", "updated_at"])

    try:
        document_text = extract_text_from_pdf(document.file.path)
        content_classification = classify_document_content(document.title, document_text)
        legacy_result = detect_ordered_chapters_with_metadata(document_text)
        resolver_result = _resolver_shadow_result(document_text)
        detection_result = _select_production_parser_result(legacy_result, resolver_result)
        detected_chapters = detection_result.accepted_chapters
    except Exception:
        document.status = DocumentStatus.FAILED
        document.save(update_fields=["status", "updated_at"])
        raise

    chapter_ids = []
    with transaction.atomic():
        document.chapters.all().delete()
        for index, chapter in enumerate(detected_chapters, start=1):
            stored_chapter = Chapter.objects.create(
                document=document,
                title=chapter.title,
                sequence_number=index,
                extracted_text=chapter.extracted_text,
            )
            chapter_ids.append(stored_chapter.id)

        document.status = DocumentStatus.PROCESSING_CONCEPTS if chapter_ids else DocumentStatus.CHAPTERS_DETECTED
        document.parser_version = "v1"
        document.parser_strategy = detection_result.strategy_used
        document.parser_confidence_score = detection_result.confidence_score
        document.parser_warnings = detection_result.warnings
        document.parser_metadata = _parser_metadata_from_detection_result(detection_result, resolver_result)
        document.content_classification = content_classification
        document.save(
            update_fields=[
                "status",
                "parser_version",
                "parser_strategy",
                "parser_confidence_score",
                "parser_warnings",
                "parser_metadata",
                "content_classification",
                "updated_at",
            ]
        )

        for chapter_id in chapter_ids:
            transaction.on_commit(lambda chapter_id=chapter_id: extract_concepts_from_chapter.delay(chapter_id))

    return len(detected_chapters)


def _resolver_shadow_result(document_text: str):
    candidates = regex_heading_candidates(document_text)
    candidates.extend(multiline_heading_candidates(document_text))
    candidates.extend(toc_like_candidates(document_text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(document_text))
    return select_best_chapter_sequence(candidates, full_text=document_text)


def _select_production_parser_result(legacy_result, resolver_result):
    if not settings.DOCUMENT_PARSER_USE_RESOLVER:
        return legacy_result

    threshold = settings.DOCUMENT_PARSER_RESOLVER_CONFIDENCE_THRESHOLD
    if resolver_result.accepted_chapters and resolver_result.confidence_score >= threshold:
        return replace(resolver_result, strategy_used="resolver")

    return replace(
        legacy_result,
        strategy_used="legacy_fallback",
        warnings=[
            *legacy_result.warnings,
            (
                "Resolver was enabled but did not meet the confidence threshold "
                f"({resolver_result.confidence_score:.2f} < {threshold:.2f}); legacy parser output was used."
            ),
        ],
    )


def _parser_metadata_from_detection_result(detection_result, resolver_result=None) -> dict:
    return {
        "accepted_chapter_count": len(detection_result.accepted_chapters),
        "rejected_candidate_count": len(detection_result.rejected_candidates),
        "accepted_chapters": [
            {
                "title": chapter.title,
                "sequence_number": chapter.sequence_number,
                "confidence_score": chapter.confidence_score,
                "detection_methods": chapter.detection_methods,
            }
            for chapter in detection_result.accepted_chapters
        ],
        "rejected_candidates": [
            {
                "title": candidate.title,
                "reason": candidate.reason,
                "detection_method": candidate.detection_method,
                "confidence_score": candidate.confidence_score,
                "evidence": candidate.evidence,
            }
            for candidate in detection_result.rejected_candidates
        ],
        "resolver_shadow": _resolver_metadata(resolver_result) if resolver_result else None,
    }


def _resolver_metadata(resolver_result) -> dict:
    return {
        "accepted_chapter_count": len(resolver_result.accepted_chapters),
        "confidence_score": resolver_result.confidence_score,
        "warnings": resolver_result.warnings,
        "accepted_chapters": [
            {
                "title": chapter.title,
                "sequence_number": chapter.sequence_number,
                "confidence_score": chapter.confidence_score,
                "detection_methods": chapter.detection_methods,
            }
            for chapter in resolver_result.accepted_chapters
        ],
    }


@shared_task
def extract_concepts_from_chapter(chapter_id: int) -> int:
    """Extract and store required concepts for one chapter in content order."""

    chapter = Chapter.objects.select_related("document").get(id=chapter_id)
    learning_content = extract_chapter_learning_content(
        chapter.title,
        chapter.extracted_text,
        chapter.document.content_classification,
        chapter.sequence_number,
    )
    detected_concepts = learning_content.teachable_concepts

    with transaction.atomic():
        chapter.chapter_summary = learning_content.chapter_summary
        chapter.chapter_objectives = learning_content.chapter_objectives
        chapter.literary_metadata = learning_content.literary_metadata or {}
        chapter.save(update_fields=["chapter_summary", "chapter_objectives", "literary_metadata", "updated_at"])

        chapter.concepts.all().delete()
        for index, concept in enumerate(detected_concepts, start=1):
            if not concept.title.strip():
                continue

            # Chapter objectives are saved on Chapter as FYI/context. They are
            # intentionally not Concept rows because students should not be
            # required to pass objectives as teachable topics.
            Concept.objects.create(
                chapter=chapter,
                title=concept.title,
                sequence_number=index,
                is_required=True,
                summary=concept.summary,
            )

    _mark_document_ready_if_concepts_are_complete(chapter.document_id)

    return len(detected_concepts)


def _mark_document_ready_if_concepts_are_complete(document_id: int) -> None:
    document = Document.objects.prefetch_related("chapters__concepts").get(id=document_id)
    chapters = list(document.chapters.all())
    if not chapters:
        return

    all_chapters_have_concepts = all(chapter.concepts.exists() for chapter in chapters)
    if all_chapters_have_concepts and document.status != DocumentStatus.READY:
        document.status = DocumentStatus.READY
        document.save(update_fields=["status", "updated_at"])
