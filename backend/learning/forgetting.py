import math
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import ConceptMastery, MasteryStrength


SLOW_RETENTION_DAYS = Decimal("30")
MEDIUM_RETENTION_DAYS = Decimal("14")
FAST_RETENTION_DAYS = Decimal("7")


def calculate_decayed_mastery(concept_mastery: ConceptMastery, current_time) -> Decimal:
    """Calculate current mastery without changing unlock or stored progress."""

    mastery_score = Decimal(str(concept_mastery.mastery_score or 0))
    if concept_mastery.last_reviewed_at is None:
        return _quantize_score(mastery_score)

    days_since_review = Decimal(str(max((current_time - concept_mastery.last_reviewed_at).total_seconds(), 0)))
    days_since_review = days_since_review / Decimal("86400")
    retention_strength = _retention_days_for_strength(concept_mastery.mastery_strength)
    decayed_score = mastery_score * Decimal(str(math.exp(float(-days_since_review / retention_strength))))
    return _quantize_score(decayed_score)


def update_forgetting_schedule(concept_mastery: ConceptMastery, mastery_score: Decimal, reviewed_at=None) -> None:
    reviewed_at = reviewed_at or timezone.now()
    strength = mastery_strength_for_score(mastery_score)
    retention_days = _retention_days_for_strength(strength)

    concept_mastery.mastery_score = _quantize_score(mastery_score)
    concept_mastery.mastery_strength = strength
    concept_mastery.last_reviewed_at = reviewed_at
    concept_mastery.next_review_at = reviewed_at + timedelta(days=float(retention_days))
    concept_mastery.forgetting_rate = (Decimal("1") / retention_days).quantize(Decimal("0.00001"))


def mastery_strength_for_score(mastery_score: Decimal) -> str:
    if mastery_score >= Decimal("90"):
        return MasteryStrength.SLOW
    if mastery_score >= Decimal("75"):
        return MasteryStrength.MEDIUM
    return MasteryStrength.FAST


def _retention_days_for_strength(mastery_strength: str) -> Decimal:
    if mastery_strength == MasteryStrength.SLOW:
        return SLOW_RETENTION_DAYS
    if mastery_strength == MasteryStrength.MEDIUM:
        return MEDIUM_RETENTION_DAYS
    return FAST_RETENTION_DAYS


def _quantize_score(score: Decimal) -> Decimal:
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
