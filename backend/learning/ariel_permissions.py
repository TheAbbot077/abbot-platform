from documents.models import Chapter, Concept

from .models import ConceptProgress, ProgressStatus


def can_teach_ariel(user, concept: Concept) -> bool:
    """Ariel can learn only concepts the student has already passed."""

    return ConceptProgress.objects.filter(
        user=user,
        concept=concept,
        status=ProgressStatus.MASTERED,
    ).exists()


def can_submit_ariel_to_examiner(user, chapter: Chapter) -> bool:
    """Examiner checks unlock only after every required concept in the chapter is passed."""

    required_concepts = chapter.concepts.filter(is_required=True)
    required_count = required_concepts.count()
    if required_count == 0:
        return False

    mastered_count = ConceptProgress.objects.filter(
        user=user,
        concept__in=required_concepts,
        status=ProgressStatus.MASTERED,
    ).count()
    return mastered_count == required_count
