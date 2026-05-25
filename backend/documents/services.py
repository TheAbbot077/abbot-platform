"""Compatibility facade for document parsing services.

The parser implementation lives in ``documents.parsing`` modules. Keep these
imports stable so existing tasks, tests, and future callers can continue using
``documents.services`` while the parser internals evolve.
"""

from .parsing.chapter_detector import (
    detect_ordered_chapters,
    detect_ordered_chapters_with_metadata,
    fallback_single_chapter_candidate,
    multiline_heading_candidates,
    regex_heading_candidates,
    toc_like_candidates,
)
from .parsing.concept_detector import detect_ordered_concepts
from .parsing.chapter_sequence_resolver import select_best_chapter_sequence
from .parsing.objective_detector import extract_chapter_learning_content
from .parsing.pdf_text_extractor import extract_text_from_pdf
from .parsing.literary_toolkit import (
    classify_document_content,
    is_literary_classification,
    is_literary_material,
    is_literary_summary,
)
from .parsing.types import (
    AcceptedChapter,
    ChapterCandidate,
    ChapterDetectionResult,
    ChapterLearningContent,
    DetectedChapter,
    DetectedConcept,
    RejectedChapterCandidate,
)


__all__ = [
    "AcceptedChapter",
    "ChapterCandidate",
    "ChapterDetectionResult",
    "ChapterLearningContent",
    "DetectedChapter",
    "DetectedConcept",
    "RejectedChapterCandidate",
    "detect_ordered_chapters",
    "detect_ordered_chapters_with_metadata",
    "detect_ordered_concepts",
    "extract_chapter_learning_content",
    "extract_text_from_pdf",
    "fallback_single_chapter_candidate",
    "classify_document_content",
    "is_literary_classification",
    "is_literary_material",
    "is_literary_summary",
    "multiline_heading_candidates",
    "regex_heading_candidates",
    "select_best_chapter_sequence",
    "toc_like_candidates",
]
