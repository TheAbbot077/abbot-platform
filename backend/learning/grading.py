from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction

from documents.models import Document

from .forgetting import update_forgetting_schedule
from .models import BloomLevel, ConceptMastery, ConceptProgress, ProgressStatus, QuizAttempt, QuizQuestion, QuizQuestionType
from .remediation import build_remediation_guidance
from .services import get_current_unlocked_concept, mark_concept_mastered


def submit_current_concept_answers(user, document: Document, submitted_answers: dict[str, str]) -> QuizAttempt | None:
    """Grade submitted answers for the current concept and update progress."""

    current = get_current_unlocked_concept(user, document)
    if current is None:
        return None

    questions = list(current.concept.quiz_questions.filter(is_answered=False).order_by("id"))
    if not questions:
        raise ValueError("No unanswered quiz questions exist for the current concept.")

    normalized_answers = {str(question_id): str(answer).strip() for question_id, answer in submitted_answers.items()}
    correct_count = 0
    missed_questions = []
    bloom_counts = {level: {"correct": 0, "total": 0} for level in BloomLevel.values}

    for question in questions:
        submitted_answer = normalized_answers.get(str(question.id), "")
        bloom_counts[question.bloom_level]["total"] += 1
        if _answer_is_correct(question, submitted_answer):
            correct_count += 1
            bloom_counts[question.bloom_level]["correct"] += 1
        else:
            missed_questions.append(question)

    score = _calculate_score(correct_count=correct_count, total_questions=len(questions))
    bloom_level_scores = _calculate_bloom_level_scores(bloom_counts)
    passed = score >= Decimal(str(settings.QUIZ_PASSING_THRESHOLD))
    remediation = "" if passed else build_remediation_guidance(missed_questions)

    with transaction.atomic():
        attempt = QuizAttempt.objects.create(
            user=user,
            concept=current.concept,
            submitted_answers=normalized_answers,
            total_questions=len(questions),
            correct_answers=correct_count,
            score=score,
            bloom_level_scores=bloom_level_scores,
            passed=passed,
            remediation=remediation,
        )

        QuizQuestion.objects.filter(id__in=[question.id for question in questions]).update(is_answered=True)

        concept_progress, _created = ConceptProgress.objects.get_or_create(user=user, concept=current.concept)
        concept_progress.attempts_count += 1
        concept_progress.last_score = score
        if not passed and concept_progress.status == ProgressStatus.LOCKED:
            concept_progress.status = ProgressStatus.UNLOCKED
        concept_progress.save(update_fields=["attempts_count", "last_score", "status", "updated_at"])
        _update_concept_mastery(user, current.concept, score, bloom_level_scores)

    if passed:
        mark_concept_mastered(user, current.concept)

    return attempt


def _calculate_score(*, correct_count: int, total_questions: int) -> Decimal:
    raw_score = Decimal(correct_count) / Decimal(total_questions) * Decimal("100")
    return raw_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _answer_is_correct(question: QuizQuestion, submitted_answer: str) -> bool:
    if question.question_type == QuizQuestionType.SHORT_ANSWER:
        return _short_answer_is_supported(question, submitted_answer)
    return submitted_answer.upper() == question.correct_option


def _short_answer_is_supported(question: QuizQuestion, submitted_answer: str) -> bool:
    """Lightweight literature check for evidence-based answers.

    This intentionally avoids requiring one exact interpretation. A short
    answer passes when it is substantive and overlaps with the official
    expected answer or evidence guidance for the current unlocked section.
    """

    normalized_answer = _normalize_text(submitted_answer)
    if len(normalized_answer.split()) < 8:
        return False

    expected_context = _normalize_text(
        " ".join([question.expected_answer, question.evidence_guidance, question.explanation])
    )
    answer_terms = {term for term in normalized_answer.split() if len(term) >= 5}
    expected_terms = {term for term in expected_context.split() if len(term) >= 5}
    if len(answer_terms & expected_terms) >= 2:
        return True

    evidence_words = {"quote", "line", "phrase", "because", "shows", "suggests", "implies", "evidence"}
    return bool(answer_terms & evidence_words) and len(normalized_answer.split()) >= 14


def _normalize_text(value: str) -> str:
    return " ".join("".join(character.lower() if character.isalnum() else " " for character in value).split())


def _calculate_bloom_level_scores(bloom_counts: dict[str, dict[str, int]]) -> dict[str, str]:
    scores = {}
    for bloom_level, counts in bloom_counts.items():
        if counts["total"] == 0:
            continue

        score = _calculate_score(correct_count=counts["correct"], total_questions=counts["total"])
        scores[bloom_level] = str(score)

    return scores


def _update_concept_mastery(user, concept, mastery_score: Decimal, bloom_level_scores: dict[str, str]) -> None:
    mastery, _created = ConceptMastery.objects.get_or_create(user=user, concept=concept)
    current_scores = mastery.bloom_level_scores or {}

    for bloom_level, score in bloom_level_scores.items():
        existing_score = Decimal(str(current_scores.get(bloom_level, "0")))
        new_score = Decimal(str(score))
        current_scores[bloom_level] = str(max(existing_score, new_score).quantize(Decimal("0.01")))

    mastery.bloom_level_scores = current_scores
    update_forgetting_schedule(mastery, mastery_score)
    mastery.save(
        update_fields=[
            "bloom_level_scores",
            "mastery_score",
            "mastery_strength",
            "last_reviewed_at",
            "next_review_at",
            "forgetting_rate",
            "updated_at",
        ]
    )
