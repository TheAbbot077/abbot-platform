import re

from .concept_detector import concept_title_from_chapter_title, detect_ordered_concepts
from .literary_toolkit import (
    build_literary_section_metadata,
    detect_literary_learning_units,
    is_literary_material,
)
from .types import ChapterLearningContent, DetectedConcept


def extract_chapter_learning_content(
    chapter_title: str,
    chapter_text: str,
    content_classification: str = "",
    section_sequence: int = 1,
) -> ChapterLearningContent:
    """Separate chapter metadata from teachable concepts.

    Chapter objectives are useful context for tutors and extraction, but they
    are not skills/topics the student should be forced to pass. Only
    teachable_concepts should become Concept records.
    """

    chapter_objectives, body_text = _separate_objectives_from_body(chapter_text)
    body_text = _remove_end_of_chapter_assessment_sections(body_text)
    literary_metadata = None
    if is_literary_material(chapter_title, body_text, content_classification):
        literary_metadata = build_literary_section_metadata(
            chapter_title,
            section_sequence,
            body_text,
            content_classification,
        )
        teachable_concepts = detect_literary_learning_units(chapter_title, body_text, content_classification)
    else:
        teachable_concepts = detect_ordered_concepts(body_text)
    if not teachable_concepts:
        fallback_title = concept_title_from_chapter_title(chapter_title)
        if fallback_title:
            teachable_concepts = [DetectedConcept(title=fallback_title, summary=_chapter_summary_from_body(body_text))]

    return ChapterLearningContent(
        chapter_title=chapter_title,
        chapter_summary=_chapter_summary_from_body(body_text),
        chapter_objectives=chapter_objectives,
        teachable_concepts=teachable_concepts,
        content_classification=content_classification or "textbook",
        literary_metadata=literary_metadata or {},
    )


def _separate_objectives_from_body(chapter_text: str) -> tuple[list[str], str]:
    objectives = []
    body_lines = []
    in_objectives = False

    for raw_line in chapter_text.splitlines():
        line = raw_line.strip()

        if _is_objectives_heading(line):
            in_objectives = True
            continue

        if in_objectives:
            if _is_chapter_body_start_heading(line):
                in_objectives = False
                body_lines.append(raw_line)
                continue

            objective = _objective_from_line(line)
            if objective:
                objectives.append(objective)
                continue

            if not line:
                continue

            if objectives:
                objectives[-1] = _clean_objective(f"{objectives[-1]} {line}")
                continue
            else:
                continue

        body_lines.append(raw_line)

    return objectives, "\n".join(body_lines).strip()


def _remove_end_of_chapter_assessment_sections(chapter_text: str) -> str:
    """Drop textbook back matter that should not become required concepts."""

    stop_pattern = re.compile(
        r"(?im)^[ \t]*(key\s+terms|chapter\s+summary|visual\s+connection\s+questions|review\s+questions|"
        r"critical\s+thinking\s+questions|study\s+questions\s+and\s+exercises|references|test\s+prep|"
        r"multiple\s+choice|free\s+response|science\s+practice\s+challenge\s+questions)[ \t]*$"
    )
    match = stop_pattern.search(chapter_text)
    return chapter_text[: match.start()].strip() if match else chapter_text


def _is_objectives_heading(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line.casefold()).strip()
    if normalized in {"objectives", "bjectives"}:
        return True
    return any(
        marker in normalized
        for marker in [
            "chapter objectives",
            "learning objectives",
            "learning outcomes",
            "you will be able to",
            "after successful completion",
        ]
    )


def _is_chapter_body_start_heading(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line.casefold()).strip()
    if normalized in {
        "introduction",
        "overview",
        "background",
    }:
        return True

    if re.match(r"^\d+(?:\.\d+)+\s+.+$", line):
        return True

    if re.match(r"^[A-Z][A-Za-z0-9 ,()/'-]{2,80}\s*[-:]\s+.+$", line):
        return True

    return False


def _objective_from_line(line: str) -> str:
    bullet_match = re.match(r"^[-*•]\s+(?P<objective>.+)$", line)
    if bullet_match:
        return _clean_objective(bullet_match.group("objective"))

    numbered_match = re.match(r"^\d+[.)]\s+(?P<objective>.+)$", line)
    if numbered_match:
        return _clean_objective(numbered_match.group("objective"))

    objective_sentence_match = re.match(
        r"^(describe|state|define|list|explain|identify|discuss|compare|summarize|recognize)\b(?P<objective>.+)$",
        line,
        flags=re.IGNORECASE,
    )
    if objective_sentence_match:
        return _clean_objective(line)

    return ""


def _clean_objective(objective: str) -> str:
    return re.sub(r"\s+", " ", objective).strip(" .;:-–")


def _chapter_summary_from_body(body_text: str) -> str:
    text = re.sub(r"\s+", " ", body_text).strip()
    if not text:
        return ""

    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    return first_sentence[:500]
