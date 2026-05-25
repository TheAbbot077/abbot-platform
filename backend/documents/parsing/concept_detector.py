import re

from .chapter_detector import is_chapter_heading_line
from .types import DetectedConcept


def detect_ordered_concepts(chapter_text: str) -> list[DetectedConcept]:
    """Detect required concepts in the order they appear in a chapter.

    This MVP extractor is intentionally simple. It favors visible structure in
    the source text and never sorts by perceived importance.
    """

    concepts = []
    seen_titles = set()

    for raw_line in chapter_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        title = _concept_title_from_line(line)
        if not title:
            continue

        normalized_title = title.casefold()
        if normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        concepts.append(DetectedConcept(title=title, summary=line))

    if concepts:
        return concepts

    fallback = fallback_concept_from_text(chapter_text)
    return [fallback] if fallback else []


def concept_title_from_chapter_title(chapter_title: str) -> str:
    title = re.sub(r"^\s*(chapter|ch\.)\s+\d+\s*[:.\-–—]?\s*", "", chapter_title, flags=re.IGNORECASE)
    title = re.sub(r"\[\d{1,5}\]", "", title)
    title = re.sub(r"\s+", " ", title).strip(" |.:-–—")
    if len(title) > 120:
        title = title[:117].rstrip() + "..."
    return title


def fallback_concept_from_text(chapter_text: str) -> DetectedConcept | None:
    text = re.sub(r"\s+", " ", chapter_text).strip()
    if not text:
        return None

    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    title = _clean_concept_title(first_sentence)
    return DetectedConcept(title=title, summary=first_sentence) if title else None


def _concept_title_from_line(line: str) -> str:
    if is_chapter_heading_line(line):
        return ""

    section_match = re.match(r"^\d+(?:\.\d+)+\s+(?P<title>.+)$", line)
    if section_match:
        return _clean_concept_title(section_match.group("title"))

    bullet_match = re.match(r"^[-*•]\s+(?P<title>.+)$", line)
    if bullet_match:
        return _clean_concept_title(bullet_match.group("title"))

    numbered_match = re.match(r"^\d+[.)]\s+(?P<title>.+)$", line)
    if numbered_match:
        return _clean_concept_title(numbered_match.group("title"))

    roman_match = re.match(r"^[ivxl]+[.)]\s+(?P<title>.+)$", line, flags=re.IGNORECASE)
    if roman_match:
        return _clean_concept_title(roman_match.group("title"))

    if re.match(r"^[A-Za-z][.)]\s+.+$", line):
        return ""

    definition_match = re.match(r"^(?P<title>[A-Z][A-Za-z0-9 ,()/'-]{2,80})\s*[-:]\s+.+$", line)
    if definition_match:
        return _clean_concept_title(definition_match.group("title"))

    if line.endswith(":") and len(line) <= 90:
        return _clean_concept_title(line[:-1])

    return ""


def _clean_concept_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" |.:-–—")
    title = re.sub(r"\s+(and|or)$", "", title, flags=re.IGNORECASE).strip(" .,:;:-–—")
    title = _normalize_concept_title(title)
    if title.casefold() in {"example", "examples", "note", "notes", "activity", "activities"}:
        return ""
    if _is_weak_concept_title(title):
        return ""
    if len(title) > 120:
        title = title[:117].rstrip() + "..."
    return title


def _normalize_concept_title(title: str) -> str:
    """Apply small deterministic wording fixes to valid concept headings."""

    title = re.sub(r"^the\s+", "", title, flags=re.IGNORECASE).strip()

    major_steps_match = re.match(
        r"^major steps in the (?P<topic>.+?) include$",
        title,
        flags=re.IGNORECASE,
    )
    if major_steps_match:
        return f"{major_steps_match.group('topic')} steps".capitalize()

    ppf_concepts_match = re.match(
        r"^ppf describes (?:three |the )?important concepts$",
        title,
        flags=re.IGNORECASE,
    )
    if ppf_concepts_match:
        return "PPF concepts"

    case_match = re.match(r"^case of (?P<topic>.+)$", title, flags=re.IGNORECASE)
    if case_match:
        return f"{case_match.group('topic')} case".capitalize()

    imperative_topic_match = re.match(
        r"^(determine|identify|describe)\s+(?P<topic>.+)$",
        title,
        flags=re.IGNORECASE,
    )
    if imperative_topic_match:
        return imperative_topic_match.group("topic").strip(" .,:;:-–").capitalize()

    return title[:1].upper() + title[1:] if title else title


def _is_weak_concept_title(title: str) -> bool:
    """Reject textbook fragments that are not stable teachable topics."""

    if not title:
        return True

    normalized = title.casefold()
    words = title.split()

    if _is_table_or_formula_artifact(title):
        return True

    if normalized in {
        "proof",
        "solution",
        "numerical example",
        "note that",
        "source",
        "available at",
        "if",
        "part i",
        "part ii",
        "part iii",
        "part iv",
        "part v",
        "q",
        "d",
    }:
        return True

    if normalized.startswith(("|", "a ", "an ", "all ", "both ")):
        return True

    if re.search(r"\b(which|following|statement|question|answer|arrange|consider|read)\b", normalized):
        return True

    if "?" in title:
        return True

    if len(words) > 10:
        return True

    if title[0].islower():
        return True

    if normalized.startswith(
        (
            "is ",
            "is because",
            "are ",
            "can ",
            "can we",
            "why ",
            "what ",
            "how ",
            "when ",
            "explain ",
            "explain why",
            "calculate ",
            "express ",
            "find ",
            "draw ",
            "if ",
            "other things",
            "according to ",
            "definition of terms",
            "effects of ",
            "define.",
            "institutes of health",
            "available at",
            "symbolically",
            "at point ",
        )
    ):
        return True

    if re.search(r"\bq[ds]?\s*=", normalized):
        return True

    if "does not change" in normalized:
        return True

    if normalized.endswith(
        (
            " the",
            " a",
            " an",
            " of",
            " to",
            " by",
            " with",
            " from",
            " in",
        )
    ):
        return True

    sentence_like_verbs = {
        "is",
        "are",
        "was",
        "were",
        "can",
        "cannot",
        "will",
        "would",
        "should",
        "has",
        "have",
        "do",
        "does",
        "did",
        "share",
        "exist",
        "exists",
        "grouped",
        "look",
        "live",
        "use",
        "uses",
        "contains",
    }
    if any(word.casefold().strip(",;:") in sentence_like_verbs for word in words[1:]):
        return True

    return False


def _is_table_or_formula_artifact(title: str) -> bool:
    compact = re.sub(r"\s+", "", title)
    word_count = len(title.split())
    digit_count = sum(character.isdigit() for character in title)
    letter_count = sum(character.isalpha() for character in title)
    formula_symbol_count = sum(character in "=/%Δ∑" for character in title)
    hyphen_count = title.count("-")

    if word_count <= 3 and formula_symbol_count and digit_count:
        return True

    if letter_count <= 3 and (digit_count or formula_symbol_count):
        return True

    if re.search(r"\b[A-Za-z]+-\d+\b", title):
        return True

    if digit_count >= 2 and hyphen_count >= 2:
        return True

    if len(compact) <= 3 and title.isupper():
        return True

    return False

