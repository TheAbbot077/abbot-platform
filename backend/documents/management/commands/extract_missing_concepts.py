from django.core.management.base import BaseCommand

from documents.models import Chapter, DocumentStatus
from documents.tasks import extract_concepts_from_chapter


class Command(BaseCommand):
    help = "Queue concept extraction for existing chapters that do not have concepts yet."

    def handle(self, *args, **options):
        chapters = Chapter.objects.filter(concepts__isnull=True).select_related("document").order_by(
            "document_id",
            "sequence_number",
        )
        queued_count = 0

        for chapter in chapters:
            document = chapter.document
            if document.status != DocumentStatus.PROCESSING_CONCEPTS:
                document.status = DocumentStatus.PROCESSING_CONCEPTS
                document.save(update_fields=["status", "updated_at"])

            extract_concepts_from_chapter.delay(chapter.id)
            queued_count += 1

        self.stdout.write(self.style.SUCCESS(f"Queued concept extraction for {queued_count} chapter(s)."))
