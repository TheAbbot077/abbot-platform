from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedChapter:
    title: str
    text: str


@dataclass(frozen=True)
class DetectedConcept:
    title: str
    summary: str = ""


@dataclass(frozen=True)
class ChapterLearningContent:
    chapter_title: str
    chapter_summary: str
    chapter_objectives: list[str]
    teachable_concepts: list[DetectedConcept]
    content_classification: str = "textbook"
    literary_metadata: dict | None = None


@dataclass(frozen=True)
class ChapterCandidate:
    title: str
    start_index: int
    end_index: int | None = None
    sequence_number: int | None = None
    detection_method: str = ""
    confidence_score: float = 0.0
    evidence: str = ""


@dataclass(frozen=True)
class AcceptedChapter:
    title: str
    sequence_number: int
    extracted_text: str
    confidence_score: float
    detection_methods: list[str]


@dataclass(frozen=True)
class RejectedChapterCandidate:
    title: str
    reason: str
    detection_method: str
    confidence_score: float
    evidence: str = ""


@dataclass(frozen=True)
class ChapterDetectionResult:
    accepted_chapters: list[AcceptedChapter]
    rejected_candidates: list[RejectedChapterCandidate]
    strategy_used: str
    confidence_score: float
    warnings: list[str]
