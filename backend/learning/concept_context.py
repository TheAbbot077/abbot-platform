import re

from documents.models import Concept
from documents.parsing.literary_toolkit import is_literary_summary


def build_concept_source_excerpt(concept: Concept, *, window: int = 1800) -> str:
    """Return concept-specific source text without exposing the whole chapter.

    The tutor and MCQ generator should work from the same narrow context. This
    keeps future locked concepts out of quizzes while still grounding the tutor
    in the original source material.
    """

    chapter_text = concept.chapter.extracted_text or ""
    if not chapter_text.strip():
        return concept.summary

    if is_literary_summary(concept.summary):
        return chapter_text[: max(window * 2, 3000)].strip()

    match = re.search(re.escape(concept.title), chapter_text, flags=re.IGNORECASE)
    if not match and concept.summary:
        match = re.search(re.escape(concept.summary[:80]), chapter_text, flags=re.IGNORECASE)

    if not match:
        return concept.summary or chapter_text[:window].strip()

    start = max(0, match.start() - window // 4)
    end = min(len(chapter_text), match.end() + window)
    return chapter_text[start:end].strip()


def normalize_for_guardrail(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
