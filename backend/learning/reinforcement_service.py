from decimal import Decimal

from .models import BloomLevel, RecommendationPriority, ReinforcementRecommendation


BLOOM_BADGE_LABELS = {
    BloomLevel.REMEMBER: "Remember Rookie",
    BloomLevel.UNDERSTAND: "Understanding Builder",
    BloomLevel.APPLY: "Application Ace",
    BloomLevel.ANALYZE: "Analysis Champ",
    BloomLevel.EVALUATE: "Master Teacher",
    BloomLevel.CREATE: "Master Teacher",
}


def build_reinforcement_copy(*, concept_title: str, score: Decimal, failed_bloom_level: str) -> dict[str, str]:
    if score < Decimal("50"):
        action = "Teach Ariel"
        priority = RecommendationPriority.HIGH
        label = "Ariel is getting rusty"
        message = f"Ariel is starting to forget {concept_title}. Give it a quick refresher lesson."
    elif score < Decimal("70"):
        action = "Explain this concept using an example"
        priority = RecommendationPriority.MEDIUM
        label = "Practice boost ready"
        message = f"Ariel's memory check needs a boost: Ariel remembered parts of {concept_title}, but needs a clearer example."
    else:
        action = "Try an apply-level question"
        priority = RecommendationPriority.LOW
        label = "Almost steady"
        message = f"Ariel is close. Try one apply-level question to lock {concept_title} back in."

    return {
        "recommended_action": action,
        "priority": priority,
        "friendly_label": label,
        "friendly_message": message,
        "mission_title": f"Rescue mission: reteach {concept_title}",
        "badge_label": BLOOM_BADGE_LABELS.get(failed_bloom_level, "Understanding Builder"),
    }


def build_teachback_memory_engine(user, subject_id=None) -> dict:
    recommendation_queryset = (
        ReinforcementRecommendation.objects.filter(user=user, resolved_at__isnull=True)
        .select_related("concept", "concept__chapter", "concept__chapter__document")
        .order_by("-created_at")
    )
    if subject_id not in (None, ""):
        recommendation_queryset = recommendation_queryset.filter(concept__chapter__document__subject_id=subject_id)

    recommendations = list(recommendation_queryset[:10])
    missions = [_serialize_recommendation(recommendation) for recommendation in recommendations]
    health_score = _memory_health_score(recommendations)

    return {
        "feature_name": "TeachBack Memory Engine",
        "headline": "Ariel is getting rusty on these concepts.",
        "memory_health": {
            "score": str(health_score),
            "label": _health_label(health_score),
        },
        "rusty_alerts": [
            mission for mission in missions if mission["priority"] in {RecommendationPriority.HIGH, RecommendationPriority.MEDIUM}
        ],
        "daily_rescue_missions": missions,
        "concept_strength_badges": [_concept_strength_badge(mission) for mission in missions],
        "reinforcement_streak": {
            "count": 0,
            "label": "Start a rescue streak by completing a refresher mission.",
        },
        "teach_back_challenge": {
            "title": "Teach-back challenge mode",
            "prompt": "Pick one rescue mission and Teach Ariel again using a fresh example.",
        },
        "bloom_mastery_badges": _bloom_badges_from_missions(missions),
    }


def _serialize_recommendation(recommendation: ReinforcementRecommendation) -> dict:
    return {
        "id": recommendation.id,
        "concept_id": recommendation.concept_id,
        "concept_title": recommendation.concept.title,
        "chapter_id": recommendation.concept.chapter_id,
        "chapter_title": recommendation.concept.chapter.title,
        "document_id": recommendation.concept.chapter.document_id,
        "document_title": recommendation.concept.chapter.document.title,
        "reason": recommendation.reason,
        "friendly_label": recommendation.friendly_label,
        "friendly_message": recommendation.friendly_message,
        "mission_title": recommendation.mission_title,
        "failed_bloom_level": recommendation.failed_bloom_level,
        "student_ai_score": str(recommendation.student_ai_score),
        "recommended_action": recommendation.recommended_action,
        "priority": recommendation.priority,
        "created_at": recommendation.created_at.isoformat(),
    }


def _memory_health_score(recommendations: list[ReinforcementRecommendation]) -> Decimal:
    if not recommendations:
        return Decimal("100.00")

    average_score = sum((recommendation.student_ai_score for recommendation in recommendations), Decimal("0"))
    return (average_score / Decimal(len(recommendations))).quantize(Decimal("0.01"))


def _health_label(score: Decimal) -> str:
    if score >= Decimal("85"):
        return "Companion memory is strong"
    if score >= Decimal("70"):
        return "A little practice keeps it sharp"
    if score >= Decimal("50"):
        return "Ariel is getting rusty"
    return "Rescue missions ready"


def _concept_strength_badge(mission: dict) -> dict:
    score = Decimal(mission["student_ai_score"])
    if score >= Decimal("80"):
        label = "Strong memory"
    elif score >= Decimal("60"):
        label = "Needs a warm-up"
    else:
        label = "Rusty but recoverable"

    return {
        "concept_id": mission["concept_id"],
        "concept_title": mission["concept_title"],
        "label": label,
        "score": mission["student_ai_score"],
    }


def _bloom_badges_from_missions(missions: list[dict]) -> list[dict]:
    seen_levels = set()
    badges = []
    for mission in missions:
        bloom_level = mission["failed_bloom_level"]
        if bloom_level in seen_levels:
            continue
        seen_levels.add(bloom_level)
        badges.append(
            {
                "bloom_level": bloom_level,
                "label": BLOOM_BADGE_LABELS.get(bloom_level, "Understanding Builder"),
                "status": "training",
            }
        )
    return badges
