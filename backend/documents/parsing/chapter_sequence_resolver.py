"""Shadow-mode chapter sequence resolver.

This module proposes a best chapter sequence from all candidate strategies, but
it is not used by production extraction yet. The current extraction task still
uses ``detect_ordered_chapters_with_metadata`` so stored Chapter rows and
learning order remain unchanged.
"""

from dataclasses import dataclass
import re

from .types import AcceptedChapter, ChapterCandidate, ChapterDetectionResult, RejectedChapterCandidate


MAX_DUPLICATE_START_DISTANCE = 25
MIN_REASONABLE_CHAPTER_LENGTH = 250


@dataclass(frozen=True)
class _CandidateGroup:
    title: str
    start_index: int
    end_index: int | None
    sequence_number: int | None
    detection_methods: list[str]
    confidence_score: float
    evidence: str
    score: float


def select_best_chapter_sequence(
    candidates: list[ChapterCandidate],
    full_text: str | None = None,
) -> ChapterDetectionResult:
    """Return the best proposed ordered chapter sequence in shadow mode.

    Scoring is intentionally simple and readable:
    - candidates supported by multiple strategies get a bonus
    - clean chapter numbers and increasing order get a bonus
    - TOC/page-reference rows and repeated page headers are penalized
    - excessive tiny chapters lower confidence because they suggest fragmentation
    """

    text = full_text or ""
    grouped_candidates = _group_duplicate_candidates(candidates)
    if not grouped_candidates:
        return ChapterDetectionResult(
            accepted_chapters=[],
            rejected_candidates=[],
            strategy_used="shadow_best_sequence_resolver",
            confidence_score=0.0,
            warnings=["Resolver found no chapter candidates."],
        )

    scored_groups = [_score_group(group, text) for group in grouped_candidates]
    winners, rejected = _choose_winners(scored_groups, text)
    warnings = _warnings_for_result(winners, scored_groups, text)
    accepted = _accepted_chapters_from_groups(winners, text)

    if not accepted:
        warnings.append("Resolver rejected all candidates; production parser should keep legacy behavior.")

    return ChapterDetectionResult(
        accepted_chapters=accepted,
        rejected_candidates=rejected,
        strategy_used="shadow_best_sequence_resolver",
        confidence_score=_confidence_for_result(winners, scored_groups, text),
        warnings=warnings,
    )


def _group_duplicate_candidates(candidates: list[ChapterCandidate]) -> list[_CandidateGroup]:
    groups: list[list[ChapterCandidate]] = []
    for candidate in sorted(candidates, key=lambda item: (item.start_index, item.detection_method)):
        matching_group = next(
            (
                group
                for group in groups
                if abs(group[0].start_index - candidate.start_index) <= MAX_DUPLICATE_START_DISTANCE
            ),
            None,
        )
        if matching_group is None:
            groups.append([candidate])
        else:
            matching_group.append(candidate)

    return [_merge_group(group) for group in groups]


def _merge_group(candidates: list[ChapterCandidate]) -> _CandidateGroup:
    best = max(candidates, key=lambda item: (item.confidence_score, len(item.title)))
    methods = sorted({candidate.detection_method for candidate in candidates})
    confidence = min(1.0, max(candidate.confidence_score for candidate in candidates) + 0.08 * (len(methods) - 1))
    sequence_number = next((candidate.sequence_number for candidate in candidates if candidate.sequence_number), None)

    return _CandidateGroup(
        title=best.title,
        start_index=min(candidate.start_index for candidate in candidates),
        end_index=best.end_index,
        sequence_number=sequence_number,
        detection_methods=methods,
        confidence_score=confidence,
        evidence=best.evidence,
        score=confidence,
    )


def _score_group(group: _CandidateGroup, text: str) -> _CandidateGroup:
    score = group.confidence_score

    if len(group.detection_methods) > 1:
        score += 0.14
    if group.sequence_number is not None:
        score += 0.10
    if "multiline_heading" in group.detection_methods:
        score += 0.12
    if _looks_like_toc_entry(group):
        score -= 0.35
    if _looks_like_repeated_page_header(group):
        score -= 0.30
    if _is_toc_only_entry(group, text):
        score -= 0.25

    return _CandidateGroup(
        title=group.title,
        start_index=group.start_index,
        end_index=group.end_index,
        sequence_number=group.sequence_number,
        detection_methods=group.detection_methods,
        confidence_score=group.confidence_score,
        evidence=group.evidence,
        score=max(0.0, min(1.0, score)),
    )


def _choose_winners(
    groups: list[_CandidateGroup],
    text: str,
) -> tuple[list[_CandidateGroup], list[RejectedChapterCandidate]]:
    best_by_sequence: dict[int, _CandidateGroup] = {}
    unnumbered: list[_CandidateGroup] = []
    rejected: list[RejectedChapterCandidate] = []

    for group in groups:
        if group.score < 0.30:
            rejected.append(_rejection(group, "low_resolver_score"))
            continue

        if group.sequence_number is None:
            unnumbered.append(group)
            continue

        existing = best_by_sequence.get(group.sequence_number)
        if existing is None or _sequence_candidate_sort_key(group, text) > _sequence_candidate_sort_key(existing, text):
            if existing is not None:
                rejected.append(_rejection(existing, "duplicate_sequence_lower_score"))
            best_by_sequence[group.sequence_number] = group
        else:
            rejected.append(_rejection(group, "duplicate_sequence_lower_score"))

    winners = sorted([*best_by_sequence.values(), *unnumbered], key=lambda group: group.start_index)

    filtered_winners = []
    last_sequence = 0
    for group in winners:
        if group.sequence_number is not None and group.sequence_number < last_sequence:
            rejected.append(_rejection(group, "sequence_number_decreases_in_text_order"))
            continue
        if group.sequence_number is not None:
            last_sequence = group.sequence_number
        filtered_winners.append(group)

    return filtered_winners, rejected


def _accepted_chapters_from_groups(groups: list[_CandidateGroup], text: str) -> list[AcceptedChapter]:
    accepted = []
    for index, group in enumerate(groups):
        start = group.start_index
        end = groups[index + 1].start_index if index + 1 < len(groups) else len(text)
        accepted.append(
            AcceptedChapter(
                title=group.title,
                sequence_number=index + 1,
                extracted_text=text[start:end].strip() if text else "",
                confidence_score=group.score,
                detection_methods=group.detection_methods,
            )
        )
    return accepted


def _sequence_candidate_sort_key(group: _CandidateGroup, text: str) -> tuple[float, int, int]:
    # Higher score wins. For likely TOC rows, a later matching body heading wins.
    return (group.score, 0 if _looks_like_toc_entry(group) else 1, group.start_index)


def _confidence_for_result(groups: list[_CandidateGroup], all_groups: list[_CandidateGroup], text: str) -> float:
    if not groups:
        return 0.0

    confidence = sum(group.score for group in groups) / len(groups)
    if _has_excessive_fragmentation(groups, text):
        confidence -= 0.20
    if len(groups) < len(all_groups) / 3:
        confidence -= 0.10
    return max(0.0, min(1.0, confidence))


def _warnings_for_result(
    winners: list[_CandidateGroup],
    all_groups: list[_CandidateGroup],
    text: str,
) -> list[str]:
    warnings = []
    if _has_excessive_fragmentation(winners, text):
        warnings.append("Resolver detected short chapter spacing that may indicate fragmented headings.")
    if len(all_groups) > max(10, len(winners) * 3):
        warnings.append("Resolver rejected many candidates; document may contain repeated page headers or a large TOC.")
    if any(_looks_like_toc_entry(group) for group in winners):
        warnings.append("Resolver accepted at least one TOC-like candidate; review dry-run output before reprocessing.")
    return warnings


def _has_excessive_fragmentation(groups: list[_CandidateGroup], text: str) -> bool:
    if len(groups) < 3 or not text:
        return False
    starts = [group.start_index for group in groups]
    lengths = [starts[index + 1] - start for index, start in enumerate(starts[:-1])]
    lengths.append(len(text) - starts[-1])
    short_count = sum(1 for length in lengths if length < MIN_REASONABLE_CHAPTER_LENGTH)
    return short_count >= max(2, len(lengths) // 2)


def _is_toc_only_entry(group: _CandidateGroup, text: str) -> bool:
    if not text or not _looks_like_toc_entry(group):
        return False
    later_text = text[group.start_index + len(group.evidence) :]
    normalized_title = _normalized_title_without_label(group.title)
    return bool(normalized_title) and normalized_title.casefold() not in later_text.casefold()


def _looks_like_toc_entry(group: _CandidateGroup) -> bool:
    evidence = group.evidence or group.title
    return "toc_like" in group.detection_methods or "..." in evidence or bool(re.search(r"(?:\.\s*){3,}\d+$", evidence))


def _looks_like_repeated_page_header(group: _CandidateGroup) -> bool:
    evidence = group.evidence.strip()
    return "|" in evidence and bool(re.search(r"\d+\s*$", evidence))


def _normalized_title_without_label(title: str) -> str:
    without_label = re.sub(r"^\s*(?:chapter|ch\.)\s+\w+\s*[:.\-]?\s*", "", title, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", without_label).strip()


def _rejection(group: _CandidateGroup, reason: str) -> RejectedChapterCandidate:
    return RejectedChapterCandidate(
        title=group.title,
        reason=reason,
        detection_method="+".join(group.detection_methods),
        confidence_score=group.score,
        evidence=group.evidence,
    )
