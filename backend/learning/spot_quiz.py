import json
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    BloomLevel,
    ConceptLesson,
    ConceptProgress,
    ProgressStatus,
    ReinforcementRecommendation,
    StudentAIMemory,
    StudentAIReinforcementReport,
    StudentAISpotQuizAttempt,
)
from .openai_client import call_openai_responses_api, extract_output_text
from .prompts import (
    EXAMINER_SPOT_GRADE_INSTRUCTIONS,
    EXAMINER_SPOT_GRADE_RESPONSE_SCHEMA,
    EXAMINER_SPOT_QUIZ_INSTRUCTIONS,
    EXAMINER_SPOT_QUIZ_RESPONSE_SCHEMA,
    build_examiner_spot_grade_input,
    build_examiner_spot_quiz_input,
)
from .reinforcement_service import build_reinforcement_copy
from .student_ai import _answer_with_openai, calculate_student_ai_retention


DEFAULT_RETENTION_THRESHOLD = Decimal("75")
DEFAULT_SPOT_QUIZ_PASSING_THRESHOLD = 80
MAX_MEMORIES_PER_RUN = 25


def run_due_student_ai_spot_quizzes(current_time=None) -> int:
    current_time = current_time or timezone.now()
    processed_count = 0

    for memory in due_student_ai_memories(current_time)[:MAX_MEMORIES_PER_RUN]:
        process_student_ai_spot_quiz(memory, current_time)
        processed_count += 1

    return processed_count


def due_student_ai_memories(current_time=None) -> list[StudentAIMemory]:
    current_time = current_time or timezone.now()
    threshold = Decimal(str(getattr(settings, "STUDENT_AI_RETENTION_REVIEW_THRESHOLD", DEFAULT_RETENTION_THRESHOLD)))
    due_memories = []

    memories = (
        StudentAIMemory.objects.select_related("user", "concept", "concept__chapter")
        .filter(next_review_at__lte=current_time)
        .order_by("next_review_at", "id")
    )
    for memory in memories:
        is_completed = ConceptProgress.objects.filter(
            user=memory.user,
            concept=memory.concept,
            status=ProgressStatus.MASTERED,
        ).exists()
        if not is_completed:
            continue

        current_retention_score = calculate_student_ai_retention(memory, current_time)
        if current_retention_score < threshold:
            memory.current_retention_score = current_retention_score
            due_memories.append(memory)

    return due_memories


def process_student_ai_spot_quiz(memory: StudentAIMemory, current_time=None) -> StudentAISpotQuizAttempt:
    current_time = current_time or timezone.now()
    official_material = _official_concept_material(memory)
    question = generate_spot_quiz_question(memory, official_material)
    retention_score = calculate_student_ai_retention(memory, current_time)
    student_ai_answer = _answer_with_openai(
        concept_id=memory.concept_id,
        concept_name=memory.concept.title,
        taught_content=memory.taught_content,
        current_retention_score=str(retention_score),
        retention_strength=memory.retention_strength,
        question=question,
    )
    grade = grade_student_ai_spot_answer(
        concept_name=memory.concept.title,
        official_material=official_material,
        question=question,
        student_ai_answer=student_ai_answer["answer"],
    )

    with transaction.atomic():
        attempt = StudentAISpotQuizAttempt.objects.create(
            user=memory.user,
            concept=memory.concept,
            memory=memory,
            question=question,
            student_ai_answer=student_ai_answer["answer"],
            score=_score_as_decimal(grade["score"]),
            passed=grade["passed"],
            feedback=grade["feedback"],
            retention_score_at_quiz=retention_score,
        )
        memory.current_retention_score = retention_score
        memory.last_spot_quiz_at = current_time
        memory.next_review_at = _next_review_time(current_time, passed=attempt.passed)
        memory.save(update_fields=["current_retention_score", "last_spot_quiz_at", "next_review_at", "updated_at"])

        if not attempt.passed:
            create_reinforcement_recommendation(memory, attempt)
            add_daily_reinforcement_recommendation(memory, attempt, current_time)

    return attempt


def generate_spot_quiz_question(memory: StudentAIMemory, official_material: str) -> str:
    payload = {
        "model": settings.OPENAI_TUTOR_MODEL,
        "instructions": EXAMINER_SPOT_QUIZ_INSTRUCTIONS,
        "input": build_examiner_spot_quiz_input(
            concept_id=memory.concept_id,
            concept_name=memory.concept.title,
            concept_summary=memory.concept.summary,
            official_concept_material=official_material,
        ),
        "text": {"format": EXAMINER_SPOT_QUIZ_RESPONSE_SCHEMA},
    }
    api_response = call_openai_responses_api(payload)
    return json.loads(extract_output_text(api_response))["question"]


def grade_student_ai_spot_answer(
    *,
    concept_name: str,
    official_material: str,
    question: str,
    student_ai_answer: str,
) -> dict:
    passing_threshold = getattr(settings, "STUDENT_AI_SPOT_QUIZ_PASSING_THRESHOLD", DEFAULT_SPOT_QUIZ_PASSING_THRESHOLD)
    payload = {
        "model": settings.OPENAI_TUTOR_MODEL,
        "instructions": EXAMINER_SPOT_GRADE_INSTRUCTIONS,
        "input": build_examiner_spot_grade_input(
            concept_name=concept_name,
            official_concept_material=official_material,
            question=question,
            student_ai_answer=student_ai_answer,
            passing_threshold=passing_threshold,
        ),
        "text": {"format": EXAMINER_SPOT_GRADE_RESPONSE_SCHEMA},
    }
    api_response = call_openai_responses_api(payload)
    grade = json.loads(extract_output_text(api_response))
    grade["passed"] = bool(grade["score"] >= passing_threshold)
    return grade


def add_daily_reinforcement_recommendation(memory: StudentAIMemory, attempt: StudentAISpotQuizAttempt, current_time) -> None:
    report, _created = StudentAIReinforcementReport.objects.get_or_create(
        user=memory.user,
        report_date=current_time.date(),
        defaults={"recommendations": []},
    )
    recommendations = report.recommendations or []
    if any(item.get("concept_id") == memory.concept_id for item in recommendations):
        return

    recommendations.append(
        {
            "concept_id": memory.concept_id,
            "concept_title": memory.concept.title,
            "retention_score": str(attempt.retention_score_at_quiz),
            "spot_quiz_score": str(attempt.score),
            "feedback": attempt.feedback,
            "recommended_action": "Teach Ariel",
        }
    )
    report.recommendations = recommendations
    report.save(update_fields=["recommendations", "updated_at"])


def create_reinforcement_recommendation(memory: StudentAIMemory, attempt: StudentAISpotQuizAttempt) -> ReinforcementRecommendation:
    existing = ReinforcementRecommendation.objects.filter(
        user=memory.user,
        concept=memory.concept,
        resolved_at__isnull=True,
    ).first()
    if existing:
        return existing

    failed_bloom_level = _failed_bloom_level_for_attempt(attempt)
    copy = build_reinforcement_copy(
        concept_title=memory.concept.title,
        score=attempt.score,
        failed_bloom_level=failed_bloom_level,
    )
    return ReinforcementRecommendation.objects.create(
        user=memory.user,
        concept=memory.concept,
        reason=_recommendation_reason(memory, attempt),
        failed_bloom_level=failed_bloom_level,
        student_ai_score=attempt.score,
        recommended_action=copy["recommended_action"],
        friendly_label=copy["friendly_label"],
        friendly_message=copy["friendly_message"],
        mission_title=copy["mission_title"],
        priority=copy["priority"],
    )


def _recommendation_reason(memory: StudentAIMemory, attempt: StudentAISpotQuizAttempt) -> str:
    return (
        f"Ariel scored {attempt.score}% on a spot quiz for {memory.concept.title}. "
        f"This suggests the retained understanding is weakening."
    )


def _failed_bloom_level_for_attempt(attempt: StudentAISpotQuizAttempt) -> str:
    if attempt.score < Decimal("50"):
        return BloomLevel.UNDERSTAND
    return BloomLevel.APPLY


def _official_concept_material(memory: StudentAIMemory) -> str:
    lesson = ConceptLesson.objects.filter(user=memory.user, concept=memory.concept).first()
    if lesson:
        return "\n\n".join([lesson.source_excerpt, lesson.explanation, "\n".join(lesson.examples)])

    return "\n\n".join([memory.concept.summary, memory.concept.chapter.extracted_text])


def _next_review_time(current_time, *, passed: bool):
    return current_time + (timedelta(days=3) if passed else timedelta(days=1))


def _score_as_decimal(score) -> Decimal:
    return Decimal(str(score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
