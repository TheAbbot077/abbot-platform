import re
from dataclasses import dataclass

from .chapter_title_cleaner import (
    append_wrapped_chapter_title_line,
    chapter_label_for_title,
    clean_chapter_title_suffix,
    has_dot_leader,
    has_trailing_page_number,
)
from .types import (
    AcceptedChapter,
    ChapterCandidate,
    ChapterDetectionResult,
    DetectedChapter,
    RejectedChapterCandidate,
)
from .chapter_sequence_resolver import select_best_chapter_sequence


LONG_DOCUMENT_CHARACTER_THRESHOLD = 30_000
TOO_MANY_CHAPTERS_THRESHOLD = 120
SUSPICIOUSLY_SHORT_CHAPTER_CHARACTER_THRESHOLD = 250
LOW_RESOLVER_CONFIDENCE_THRESHOLD = 0.55

WRITTEN_CHAPTER_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
CHAPTER_NUMBER_PATTERN = rf"\d+|{'|'.join(WRITTEN_CHAPTER_NUMBERS)}"
CHAPTER_HEADING_PATTERN = re.compile(
    rf"(?im)^[ \t]*(?P<label>chapter[ \t]+(?:{CHAPTER_NUMBER_PATTERN})|ch\.[ \t]*\d+)[ \t]*[:.\-–]?[ \t]*(?P<title>[^\n\r]*)$"
)
MULTILINE_CHAPTER_HEADING_PATTERN = re.compile(
    rf"(?m)^[ \t]*(?P<label>CHAPTER[ \t]*(?:\r?\n)[ \t]*(?:\d+))[ \t]*\r?\n[ \t]*(?P<title>[^\n\r]+)$"
)


@dataclass(frozen=True)
class _ChapterHeadingCandidate:
    match: re.Match
    chapter_key: int | str
    score: int
    title_override: str = ""


def detect_ordered_chapters(document_text: str) -> list[DetectedChapter]:
    """Detect chapters in the order they appear in extracted document text.

    The returned list position is the only source used for chapter sequence
    numbers. Async task completion time and model timestamps are intentionally
    irrelevant to ordering.
    """

    result = detect_ordered_chapters_with_metadata(document_text)
    return [
        DetectedChapter(title=chapter.title, text=chapter.extracted_text)
        for chapter in result.accepted_chapters
    ]


def detect_ordered_chapters_with_metadata(document_text: str) -> ChapterDetectionResult:
    """Detect chapters with parser metadata for future strategy auditing."""

    text = document_text.strip()
    if not text:
        return ChapterDetectionResult(
            accepted_chapters=[],
            rejected_candidates=[],
            strategy_used="empty_document",
            confidence_score=0.0,
            warnings=["No text was extracted from the document."],
        )

    candidates = _select_chapter_heading_candidates(text)
    if not candidates:
        fallback_chapters = [
            AcceptedChapter(
                title="Chapter 1",
                sequence_number=1,
                extracted_text=text,
                confidence_score=0.35,
                detection_methods=["single_chapter_fallback"],
            )
        ]
        resolver_result = select_best_chapter_sequence(_all_strategy_candidates(text), full_text=text)
        return ChapterDetectionResult(
            accepted_chapters=fallback_chapters,
            rejected_candidates=[],
            strategy_used="single_chapter_fallback",
            confidence_score=0.35,
            warnings=_parser_warnings(
                text,
                fallback_chapters,
                [],
                resolver_result,
                extra_warnings=["No explicit chapter headings were detected; stored the document as one chapter."],
            ),
        )

    chapters = []
    for index, candidate in enumerate(candidates):
        match = candidate.match
        start = match.start()
        end = candidates[index + 1].match.start() if index + 1 < len(candidates) else len(text)
        heading = match.group(0).strip()
        title_suffix = candidate.title_override or clean_chapter_title_suffix(match.group("title"))
        title_suffix = append_wrapped_chapter_title_line(text, match.end(), title_suffix)
        label = chapter_label_for_title(match.group("label"))
        title = heading if not title_suffix else f"{label}: {title_suffix}"
        chapter_text = text[start:end].strip()
        chapters.append(
            AcceptedChapter(
                title=title,
                sequence_number=index + 1,
                extracted_text=chapter_text,
                confidence_score=_confidence_from_score(candidate.score),
                detection_methods=[_detection_method_for_match(match)],
            )
        )

    rejected_candidates = _build_rejected_candidates(text, candidates)
    resolver_result = select_best_chapter_sequence(_all_strategy_candidates(text), full_text=text)

    return ChapterDetectionResult(
        accepted_chapters=chapters,
        rejected_candidates=rejected_candidates,
        strategy_used=_strategy_used_for_candidates(candidates),
        confidence_score=_average_confidence(chapters),
        warnings=_parser_warnings(text, chapters, rejected_candidates, resolver_result),
    )


def is_chapter_heading_line(line: str) -> bool:
    return bool(CHAPTER_HEADING_PATTERN.match(line))


def regex_heading_candidates(text: str) -> list[ChapterCandidate]:
    return [
        ChapterCandidate(
            title=_display_title_from_match(match),
            start_index=match.start(),
            end_index=match.end(),
            sequence_number=_optional_sequence_number_from_label(match.group("label")),
            detection_method="regex_heading",
            confidence_score=_confidence_from_score(_chapter_heading_score(match.group("title"))),
            evidence=match.group(0).strip(),
        )
        for match in CHAPTER_HEADING_PATTERN.finditer(text)
    ]


def multiline_heading_candidates(text: str) -> list[ChapterCandidate]:
    return [
        ChapterCandidate(
            title=_display_title_from_match(match),
            start_index=match.start(),
            end_index=match.end(),
            sequence_number=_optional_sequence_number_from_label(match.group("label")),
            detection_method="multiline_heading",
            confidence_score=1.0,
            evidence=match.group(0).strip(),
        )
        for match in MULTILINE_CHAPTER_HEADING_PATTERN.finditer(text)
    ]


def toc_like_candidates(text: str) -> list[ChapterCandidate]:
    return [
        ChapterCandidate(
            title=_display_title_from_match(match),
            start_index=match.start(),
            end_index=match.end(),
            sequence_number=_optional_sequence_number_from_label(match.group("label")),
            detection_method="toc_like",
            confidence_score=0.25,
            evidence=match.group(0).strip(),
        )
        for match in CHAPTER_HEADING_PATTERN.finditer(text)
        if _is_table_of_contents_chapter_heading(match.group("title"))
    ]


def fallback_single_chapter_candidate(text: str) -> list[ChapterCandidate]:
    stripped_text = text.strip()
    if not stripped_text:
        return []

    return [
        ChapterCandidate(
            title="Chapter 1",
            start_index=0,
            end_index=len(stripped_text),
            sequence_number=1,
            detection_method="fallback_single_chapter",
            confidence_score=0.35,
            evidence=stripped_text[:300],
        )
    ]


def _select_chapter_heading_candidates(text: str) -> list[_ChapterHeadingCandidate]:
    """Return likely top-level chapter starts, not TOC rows or page headers."""

    best_by_chapter_key: dict[int | str, _ChapterHeadingCandidate] = {}
    toc_title_by_chapter_key: dict[int | str, str] = {}
    unique_candidates: list[_ChapterHeadingCandidate] = []
    multiline_matches = list(MULTILINE_CHAPTER_HEADING_PATTERN.finditer(text))
    heading_matches = (
        multiline_matches
        if len({_chapter_key_from_label(match.group("label")) for match in multiline_matches}) >= 2
        else list(CHAPTER_HEADING_PATTERN.finditer(text))
    )

    for match in CHAPTER_HEADING_PATTERN.finditer(text):
        chapter_key = _chapter_key_from_label(match.group("label"))
        clean_title = clean_chapter_title_suffix(match.group("title"))
        if _is_table_of_contents_chapter_heading(match.group("title")) and clean_title:
            toc_title_by_chapter_key.setdefault(chapter_key, clean_title)

    for match in heading_matches:
        if CHAPTER_HEADING_PATTERN.match(match.group(0)) and _is_table_of_contents_chapter_heading(match.group("title")):
            continue

        candidate = _ChapterHeadingCandidate(
            match=match,
            chapter_key=_chapter_key_from_label(match.group("label")),
            score=_chapter_heading_score(match.group("title")),
        )

        existing = best_by_chapter_key.get(candidate.chapter_key)
        if existing is None:
            best_by_chapter_key[candidate.chapter_key] = candidate
            unique_candidates.append(candidate)
            continue

        if candidate.score > existing.score:
            best_by_chapter_key[candidate.chapter_key] = candidate
            unique_candidates = [
                candidate if item.chapter_key == candidate.chapter_key else item
                for item in unique_candidates
            ]

    candidates = []
    for candidate in sorted(unique_candidates, key=lambda item: item.match.start()):
        candidates.append(
            _ChapterHeadingCandidate(
                match=candidate.match,
                chapter_key=candidate.chapter_key,
                score=candidate.score,
                title_override=toc_title_by_chapter_key.get(candidate.chapter_key, ""),
            )
        )

    return candidates


def _build_rejected_candidates(
    text: str,
    accepted_candidates: list[_ChapterHeadingCandidate],
) -> list[RejectedChapterCandidate]:
    accepted_starts = {candidate.match.start() for candidate in accepted_candidates}
    rejected = []

    for candidate in _all_strategy_candidates(text):
        if candidate.start_index in accepted_starts:
            continue

        reason = "duplicate_or_lower_confidence_candidate"
        if candidate.detection_method == "toc_like":
            reason = "table_of_contents_or_page_reference"

        rejected.append(
            RejectedChapterCandidate(
                title=candidate.title,
                reason=reason,
                detection_method=candidate.detection_method,
                confidence_score=candidate.confidence_score,
                evidence=candidate.evidence,
            )
        )

    return rejected


def _all_strategy_candidates(text: str) -> list[ChapterCandidate]:
    candidates = regex_heading_candidates(text)
    candidates.extend(multiline_heading_candidates(text))
    candidates.extend(toc_like_candidates(text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(text))
    return sorted(candidates, key=lambda candidate: (candidate.start_index, candidate.detection_method))


def _parser_warnings(
    text: str,
    accepted_chapters: list[AcceptedChapter],
    rejected_candidates: list[RejectedChapterCandidate],
    resolver_result: ChapterDetectionResult,
    extra_warnings: list[str] | None = None,
) -> list[str]:
    warnings = list(extra_warnings or [])
    all_candidates = _all_strategy_candidates(text)

    if len(accepted_chapters) == 1 and len(text) >= LONG_DOCUMENT_CHARACTER_THRESHOLD:
        warnings.append("Only one chapter was detected in a long document; review the parser dry run before reprocessing.")

    if len(accepted_chapters) > TOO_MANY_CHAPTERS_THRESHOLD:
        warnings.append(
            f"{len(accepted_chapters)} chapters were detected, which may indicate page headers or subsections were parsed as chapters."
        )

    duplicate_sequences = _repeated_duplicate_sequence_numbers(all_candidates)
    if duplicate_sequences:
        warnings.append(
            "Repeated duplicate chapter numbers were detected: "
            + ", ".join(f"Chapter {number} appeared {count} times" for number, count in duplicate_sequences[:5])
            + "."
        )

    if _has_large_chapter_gaps(accepted_chapters):
        warnings.append("Large gaps were detected between chapter starts; one or more chapters may be missing.")

    short_count = _suspiciously_short_chapter_count(accepted_chapters)
    if short_count:
        warnings.append(f"{short_count} suspiciously short chapter(s) were detected; check for fragmented headings.")

    if _has_toc_candidates_without_body_matches(all_candidates, accepted_chapters):
        warnings.append("TOC-like chapter candidates were found without matching body chapters.")

    if _legacy_and_resolver_disagree_significantly(accepted_chapters, resolver_result.accepted_chapters):
        warnings.append("Legacy parser output and shadow resolver output disagree significantly.")

    if resolver_result.confidence_score < LOW_RESOLVER_CONFIDENCE_THRESHOLD:
        warnings.append(f"Shadow resolver confidence is low ({resolver_result.confidence_score:.2f}).")

    warnings.extend(resolver_result.warnings)
    return _deduplicate_warnings(warnings)


def _repeated_duplicate_sequence_numbers(candidates: list[ChapterCandidate]) -> list[tuple[int, int]]:
    counts: dict[int, set[int]] = {}
    for candidate in candidates:
        if candidate.sequence_number is None:
            continue
        counts.setdefault(candidate.sequence_number, set()).add(candidate.start_index)

    duplicates = [(number, len(starts)) for number, starts in counts.items() if len(starts) >= 3]
    return sorted(duplicates, key=lambda item: item[0])


def _has_large_chapter_gaps(accepted_chapters: list[AcceptedChapter]) -> bool:
    chapter_lengths = [len(chapter.extracted_text) for chapter in accepted_chapters if chapter.extracted_text.strip()]
    if len(chapter_lengths) < 3:
        return False

    median_length = sorted(chapter_lengths)[len(chapter_lengths) // 2]
    return any(length > max(8_000, median_length * 5) for length in chapter_lengths)


def _suspiciously_short_chapter_count(accepted_chapters: list[AcceptedChapter]) -> int:
    if len(accepted_chapters) < 3:
        return 0
    return sum(
        1
        for chapter in accepted_chapters
        if len(chapter.extracted_text.strip()) < SUSPICIOUSLY_SHORT_CHAPTER_CHARACTER_THRESHOLD
    )


def _has_toc_candidates_without_body_matches(
    candidates: list[ChapterCandidate],
    accepted_chapters: list[AcceptedChapter],
) -> bool:
    toc_titles = {
        _normalized_chapter_title(candidate.title)
        for candidate in candidates
        if candidate.detection_method == "toc_like"
    }
    if not toc_titles:
        return False

    accepted_titles = {_normalized_chapter_title(chapter.title) for chapter in accepted_chapters}
    return any(title and title not in accepted_titles for title in toc_titles)


def _legacy_and_resolver_disagree_significantly(
    legacy_chapters: list[AcceptedChapter],
    resolver_chapters: list[AcceptedChapter],
) -> bool:
    if not legacy_chapters and not resolver_chapters:
        return False
    if abs(len(legacy_chapters) - len(resolver_chapters)) >= max(2, len(legacy_chapters) // 4):
        return True

    compared_count = min(len(legacy_chapters), len(resolver_chapters))
    if compared_count == 0:
        return True

    mismatches = sum(
        1
        for index in range(compared_count)
        if _normalized_chapter_title(legacy_chapters[index].title)
        != _normalized_chapter_title(resolver_chapters[index].title)
    )
    return mismatches / compared_count >= 0.35


def _normalized_chapter_title(title: str) -> str:
    title = re.sub(r"^\s*(?:chapter|ch\.)\s+\w+\s*[:.\-]?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title)
    return title.strip().casefold()


def _deduplicate_warnings(warnings: list[str]) -> list[str]:
    seen = set()
    unique_warnings = []
    for warning in warnings:
        if warning in seen:
            continue
        seen.add(warning)
        unique_warnings.append(warning)
    return unique_warnings


def _detection_method_for_match(match: re.Match) -> str:
    if "\n" in match.group("label"):
        return "multiline_chapter_heading"
    return "one_line_chapter_heading"


def _strategy_used_for_candidates(candidates: list[_ChapterHeadingCandidate]) -> str:
    if any(_detection_method_for_match(candidate.match) == "multiline_chapter_heading" for candidate in candidates):
        return "multiline_chapter_heading"
    return "one_line_chapter_heading"


def _confidence_from_score(score: int) -> float:
    return max(0.0, min(1.0, score / 100))


def _average_confidence(chapters: list[AcceptedChapter]) -> float:
    if not chapters:
        return 0.0
    return sum(chapter.confidence_score for chapter in chapters) / len(chapters)


def _chapter_key_from_label(label: str) -> int | str:
    normalized = re.sub(r"\s+", " ", label.casefold()).strip()
    number_text = normalized.replace("chapter", "").replace("ch.", "").strip()
    if number_text.isdigit():
        return int(number_text)
    return WRITTEN_CHAPTER_NUMBERS.get(number_text, normalized)


def _optional_sequence_number_from_label(label: str) -> int | None:
    chapter_key = _chapter_key_from_label(label)
    return chapter_key if isinstance(chapter_key, int) else None


def _display_title_from_match(match: re.Match) -> str:
    title = clean_chapter_title_suffix(match.group("title"))
    title = append_wrapped_chapter_title_line(match.string, match.end(), title)
    label = chapter_label_for_title(match.group("label"))
    return f"{label}: {title}" if title else label


def _chapter_heading_score(title_suffix: str) -> int:
    title = title_suffix.strip()
    score = 100

    if not title:
        score -= 60
    if "|" in title:
        score -= 80
    if has_dot_leader(title):
        score -= 100
    if has_trailing_page_number(title):
        score -= 50
    if "..." in title:
        score -= 100

    return score


def _is_table_of_contents_chapter_heading(title_suffix: str) -> bool:
    title = title_suffix.strip()
    if "..." in title or has_dot_leader(title):
        return True
    return False
