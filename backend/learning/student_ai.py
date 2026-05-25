import json
import math
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from documents.models import Concept

from .forgetting import FAST_RETENTION_DAYS, MEDIUM_RETENTION_DAYS, SLOW_RETENTION_DAYS, mastery_strength_for_score
from .models import MasteryStrength, StudentAIMemory
from .openai_client import call_openai_responses_api, extract_output_text
from .prompts import (
    STUDENT_AI_ANSWER_INSTRUCTIONS,
    STUDENT_AI_ANSWER_RESPONSE_SCHEMA,
    build_student_ai_answer_input,
)


def teach_student_ai_memory(user, concept: Concept, taught_content: str, initial_mastery_score: Decimal) -> StudentAIMemory:
    """Store what the human student taught Ariel for one concept."""

    taught_at = timezone.now()
    initial_mastery_score = _clamp_score(initial_mastery_score)
    retention_strength = mastery_strength_for_score(initial_mastery_score)
    next_review_at = taught_at + _review_interval_for_strength(retention_strength)

    memory, _created = StudentAIMemory.objects.update_or_create(
        user=user,
        concept=concept,
        defaults={
            "taught_content": taught_content,
            "taught_at": taught_at,
            "initial_mastery_score": initial_mastery_score,
            "current_retention_score": initial_mastery_score,
            "retention_strength": retention_strength,
            "last_spot_quiz_at": None,
            "next_review_at": next_review_at,
        },
    )
    return memory


def answer_student_ai_question(user, concept: Concept, question: str) -> dict:
    memory = StudentAIMemory.objects.filter(user=user, concept=concept).first()
    if memory is None:
        raise ValueError("Teach Ariel this concept before asking questions.")

    current_retention_score = calculate_student_ai_retention(memory, timezone.now())
    memory.current_retention_score = current_retention_score
    memory.last_spot_quiz_at = timezone.now()
    memory.save(update_fields=["current_retention_score", "last_spot_quiz_at", "updated_at"])

    return _answer_with_openai(
        concept_id=concept.id,
        concept_name=concept.title,
        taught_content=memory.taught_content,
        current_retention_score=str(current_retention_score),
        retention_strength=memory.retention_strength,
        question=question,
    )


def calculate_student_ai_retention(memory: StudentAIMemory, current_time) -> Decimal:
    retention_days = _retention_days_for_strength(memory.retention_strength)
    days_since_taught = Decimal(str(max((current_time - memory.taught_at).total_seconds(), 0))) / Decimal("86400")
    retained_score = Decimal(str(memory.initial_mastery_score)) * Decimal(
        str(math.exp(float(-days_since_taught / retention_days)))
    )
    return _clamp_score(retained_score)


def _answer_with_openai(
    *,
    concept_id: int,
    concept_name: str,
    taught_content: str,
    current_retention_score: str,
    retention_strength: str,
    question: str,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise ImproperlyConfigured("OPENAI_API_KEY is required for Ariel answers.")

    payload = {
        "model": settings.OPENAI_TUTOR_MODEL,
        "instructions": STUDENT_AI_ANSWER_INSTRUCTIONS,
        "input": build_student_ai_answer_input(
            concept_id=concept_id,
            concept_name=concept_name,
            taught_content=taught_content,
            current_retention_score=current_retention_score,
            retention_strength=retention_strength,
            question=question,
        ),
        "text": {"format": STUDENT_AI_ANSWER_RESPONSE_SCHEMA},
    }
    api_response = call_openai_responses_api(payload)
    return json.loads(extract_output_text(api_response))


def _retention_days_for_strength(retention_strength: str) -> Decimal:
    if retention_strength == MasteryStrength.SLOW:
        return SLOW_RETENTION_DAYS
    if retention_strength == MasteryStrength.MEDIUM:
        return MEDIUM_RETENTION_DAYS
    return FAST_RETENTION_DAYS


def _review_interval_for_strength(retention_strength: str):
    from datetime import timedelta

    return timedelta(days=float(_retention_days_for_strength(retention_strength)))


def _clamp_score(score: Decimal) -> Decimal:
    score = max(Decimal("0"), min(Decimal("100"), Decimal(str(score))))
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
