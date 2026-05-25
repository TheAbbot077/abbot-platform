import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from documents.models import Document
from documents.parsing.literary_toolkit import is_literary_summary

from .concept_context import normalize_for_guardrail
from .models import BloomLevel, ConceptLesson, QuizQuestion, QuizQuestionType
from .openai_client import call_openai_responses_api, extract_output_text
from .prompts import MCQ_INSTRUCTIONS, MCQ_RESPONSE_SCHEMA, build_mcq_input
from .services import get_current_unlocked_concept


DEFAULT_MCQ_COUNT = 3
MAX_MCQ_COUNT = 5
MIN_MCQ_COUNT = 1
FIRST_ATTEMPT = "first_attempt"
REINFORCEMENT_ATTEMPT = "reinforcement_attempt"

BASIC_BLOOM_LEVELS = [BloomLevel.REMEMBER, BloomLevel.UNDERSTAND]
STRONGER_BLOOM_LEVELS = [BloomLevel.APPLY, BloomLevel.ANALYZE]
REINFORCEMENT_BLOOM_LEVELS = [BloomLevel.APPLY, BloomLevel.ANALYZE, BloomLevel.EVALUATE]
MCQ_ALLOWED_BLOOM_LEVELS = [*BASIC_BLOOM_LEVELS, *REINFORCEMENT_BLOOM_LEVELS]


def get_or_generate_current_concept_mcqs(user, document: Document, question_count: int = DEFAULT_MCQ_COUNT) -> list[QuizQuestion]:
    """Return unanswered MCQs for the current unlocked concept, generating once if needed."""

    current = get_current_unlocked_concept(user, document)
    if current is None:
        return []

    concept = current.concept
    lesson = ConceptLesson.objects.filter(user=user, concept=concept).first()
    if lesson is None:
        raise ValueError("Teach the current concept before generating practice questions.")

    # Clarification chat helps understanding but is not automatically testable.
    # MCQs intentionally use only the official stored concept lesson, not
    # TutorMessage follow-ups or general-knowledge add-ons.
    existing_questions = list(concept.quiz_questions.filter(is_answered=False).order_by("id"))
    if existing_questions:
        return existing_questions

    question_count = max(MIN_MCQ_COUNT, min(question_count, MAX_MCQ_COUNT))
    attempt_mode = _mcq_attempt_mode(user, concept)
    bloom_distribution = _bloom_distribution_for_attempt(attempt_mode, question_count)
    generated_questions = _generate_mcqs_with_openai(
        concept_id=concept.id,
        concept_name=concept.title,
        concept_summary=concept.summary,
        source_excerpt=lesson.source_excerpt,
        tutor_explanation=lesson.explanation,
        tutor_examples=lesson.examples,
        question_count=question_count,
        attempt_mode=attempt_mode,
        bloom_distribution=bloom_distribution,
        locked_concept_titles=_future_locked_concept_titles(concept),
    )

    with transaction.atomic():
        stored_questions = []
        for question in generated_questions[:MAX_MCQ_COUNT]:
            stored_questions.append(
                QuizQuestion.objects.create(
                    concept=concept,
                    question_type=_validated_question_type(question.get("question_type"), concept.summary),
                    question_text=question["question_text"],
                    option_a=question["options"]["A"],
                    option_b=question["options"]["B"],
                    option_c=question["options"]["C"],
                    option_d=question["options"]["D"],
                    correct_option=question["correct_option"],
                    explanation=question["explanation"],
                    expected_answer=question.get("expected_answer", ""),
                    evidence_guidance=question.get("evidence_guidance", ""),
                    bloom_level=_validated_bloom_level(question.get("bloom_level")),
                )
            )

    return stored_questions


def _generate_mcqs_with_openai(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str = "",
    source_excerpt: str,
    tutor_explanation: str,
    tutor_examples: list[str],
    question_count: int,
    attempt_mode: str,
    bloom_distribution: dict[str, int],
    locked_concept_titles: list[str] | None = None,
) -> list[dict]:
    if not settings.OPENAI_API_KEY:
        raise ImproperlyConfigured("OPENAI_API_KEY is required to generate MCQs.")

    accepted_questions = []
    attempts = 0
    locked_concept_titles = locked_concept_titles or []

    while len(accepted_questions) < question_count and attempts < 2:
        attempts += 1
        remaining_count = question_count - len(accepted_questions)
        payload = {
            "model": settings.OPENAI_TUTOR_MODEL,
            "instructions": MCQ_INSTRUCTIONS,
            "input": build_mcq_input(
                concept_id=concept_id,
                concept_name=concept_name,
                concept_summary=concept_summary,
                source_excerpt=source_excerpt,
                tutor_explanation=tutor_explanation,
                tutor_examples=tutor_examples,
                question_count=remaining_count,
                attempt_mode=attempt_mode,
                bloom_distribution=_remaining_bloom_distribution(bloom_distribution, accepted_questions),
            ),
            "text": {"format": MCQ_RESPONSE_SCHEMA},
        }

        api_response = call_openai_responses_api(payload)
        parsed_response = json.loads(extract_output_text(api_response))
        for question in parsed_response["questions"]:
            if _question_matches_current_concept(
                question,
                concept_name=concept_name,
                concept_summary=concept_summary,
                tutor_explanation=tutor_explanation,
                tutor_examples=tutor_examples,
                locked_concept_titles=locked_concept_titles,
                allowed_bloom_levels=list(bloom_distribution.keys()),
            ):
                accepted_questions.append(question)

    return accepted_questions[:question_count]


def _question_matches_current_concept(
    question: dict,
    *,
    concept_name: str,
    concept_summary: str = "",
    tutor_explanation: str,
    tutor_examples: list[str],
    locked_concept_titles: list[str],
    allowed_bloom_levels: list[str] | None = None,
) -> bool:
    allowed_bloom_levels = allowed_bloom_levels or MCQ_ALLOWED_BLOOM_LEVELS
    if _validated_bloom_level(question.get("bloom_level")) not in allowed_bloom_levels:
        return False

    question_type = _validated_question_type(question.get("question_type"), concept_summary)
    if question_type == QuizQuestionType.SHORT_ANSWER and not is_literary_summary(concept_summary):
        return False
    if question_type == QuizQuestionType.SHORT_ANSWER:
        if not str(question.get("expected_answer", "")).strip():
            return False
    else:
        options = question.get("options", {})
        if not isinstance(options, dict) or not all(str(options.get(option, "")).strip() for option in ["A", "B", "C", "D"]):
            return False
        if question.get("correct_option") not in {"A", "B", "C", "D"}:
            return False

    question_blob = " ".join(
        [
            str(question.get("question_text", "")),
            " ".join(str(value) for value in question.get("options", {}).values()),
            str(question.get("explanation", "")),
            str(question.get("expected_answer", "")),
            str(question.get("evidence_guidance", "")),
        ]
    )
    normalized_question = normalize_for_guardrail(question_blob)

    for locked_title in locked_concept_titles:
        normalized_locked_title = normalize_for_guardrail(locked_title)
        if len(normalized_locked_title) >= 12 and normalized_locked_title in normalized_question:
            return False

    allowed_context = normalize_for_guardrail(" ".join([concept_name, tutor_explanation, *tutor_examples]))
    if is_literary_summary(concept_summary):
        allowed_context = normalize_for_guardrail(" ".join([tutor_explanation, *tutor_examples]))
    important_terms = [
        term
        for term in normalize_for_guardrail(concept_name).split()
        if len(term) >= 4
    ]
    if important_terms and any(term in normalized_question for term in important_terms):
        return True

    question_terms = {term for term in normalized_question.split() if len(term) >= 5}
    context_terms = {term for term in allowed_context.split() if len(term) >= 5}
    return len(question_terms & context_terms) >= 2


def _mcq_attempt_mode(user, concept) -> str:
    has_previous_attempt = concept.quiz_attempts.filter(user=user).exists()
    return REINFORCEMENT_ATTEMPT if has_previous_attempt else FIRST_ATTEMPT


def _bloom_distribution_for_attempt(attempt_mode: str, question_count: int) -> dict[str, int]:
    """Return target Bloom counts while keeping MCQs inside supported levels."""

    question_count = max(MIN_MCQ_COUNT, min(question_count, MAX_MCQ_COUNT))
    if attempt_mode == REINFORCEMENT_ATTEMPT:
        basic_count = max(1, round(question_count * 0.30))
        advanced_count = question_count - basic_count
        return {
            **_spread_levels(BASIC_BLOOM_LEVELS, basic_count),
            **_spread_levels(REINFORCEMENT_BLOOM_LEVELS, advanced_count),
        }

    basic_count = max(1, round(question_count * 0.60))
    advanced_count = question_count - basic_count
    return {
        **_spread_levels(BASIC_BLOOM_LEVELS, basic_count),
        **_spread_levels(STRONGER_BLOOM_LEVELS, advanced_count),
    }


def _spread_levels(levels: list[str], count: int) -> dict[str, int]:
    distribution = {level: 0 for level in levels}
    for index in range(count):
        distribution[levels[index % len(levels)]] += 1
    return {level: total for level, total in distribution.items() if total > 0}


def _remaining_bloom_distribution(target_distribution: dict[str, int], accepted_questions: list[dict]) -> dict[str, int]:
    remaining = target_distribution.copy()
    for question in accepted_questions:
        bloom_level = _validated_bloom_level(question.get("bloom_level"))
        if bloom_level in remaining:
            remaining[bloom_level] = max(0, remaining[bloom_level] - 1)
    return {level: total for level, total in remaining.items() if total > 0}


def _validated_bloom_level(value: str | None) -> str:
    if value in MCQ_ALLOWED_BLOOM_LEVELS:
        return value
    return BloomLevel.UNDERSTAND


def _validated_question_type(value: str | None, concept_summary: str = "") -> str:
    if value == QuizQuestionType.SHORT_ANSWER and is_literary_summary(concept_summary):
        return QuizQuestionType.SHORT_ANSWER
    return QuizQuestionType.MULTIPLE_CHOICE


def _future_locked_concept_titles(concept) -> list[str]:
    return list(
        concept.chapter.concepts.filter(sequence_number__gt=concept.sequence_number)
        .order_by("sequence_number")
        .values_list("title", flat=True)
    )
