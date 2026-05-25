from django.db import transaction

from learning.models import StudentAIReinforcementReport

from .models import Document


def delete_document_tree(document: Document) -> None:
    """Delete a textbook, its ordered content, progress records, and stored file."""

    owner = document.owner
    concept_ids = list(document.chapters.values_list("concepts__id", flat=True))
    file_field = document.file
    file_name = file_field.name
    storage = file_field.storage

    with transaction.atomic():
        document.delete()
        _remove_stale_recommendations_from_daily_reports(owner, concept_ids)

    if file_name and storage.exists(file_name):
        storage.delete(file_name)


def _remove_stale_recommendations_from_daily_reports(owner, concept_ids: list[int]) -> None:
    concept_id_set = {concept_id for concept_id in concept_ids if concept_id}
    if not concept_id_set:
        return

    reports = StudentAIReinforcementReport.objects.filter(user=owner)
    for report in reports:
        recommendations = [
            recommendation
            for recommendation in (report.recommendations or [])
            if recommendation.get("concept_id") not in concept_id_set
        ]
        if recommendations == report.recommendations:
            continue

        report.recommendations = recommendations
        report.save(update_fields=["recommendations", "updated_at"])
