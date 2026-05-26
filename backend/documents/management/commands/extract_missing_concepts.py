from django.core.management.base import BaseCommand

from documents.models import Chapter, DocumentStatus
from documents.tasks import extract_concepts_from_chapter


class Command(BaseCommand):
    help = "Extract concepts for existing chapters that do not have concepts yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Only extract missing concepts for one document.",
        )
        parser.add_argument(
            "--queue",
            action="store_true",
            help="Queue missing concept extraction in Celery instead of running it immediately.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Process at most this many chapters.",
        )

    def handle(self, *args, **options):
        chapters = Chapter.objects.filter(concepts__isnull=True).select_related("document").distinct().order_by(
            "document_id",
            "sequence_number",
        )
        if options.get("document_id"):
            chapters = chapters.filter(document_id=options["document_id"])
        if options.get("limit"):
            chapters = chapters[: options["limit"]]

        processed_count = 0
        failed_count = 0

        for chapter in chapters:
            document = chapter.document
            if document.status != DocumentStatus.PROCESSING_CONCEPTS:
                document.status = DocumentStatus.PROCESSING_CONCEPTS
                document.save(update_fields=["status", "updated_at"])

            if options["queue"]:
                extract_concepts_from_chapter.delay(chapter.id)
                processed_count += 1
                continue

            try:
                concept_count = extract_concepts_from_chapter(chapter.id)
            except Exception as exc:  # pragma: no cover - operational diagnostic output
                failed_count += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed chapter {chapter.id} "
                        f"({document.title} - {chapter.sequence_number}. {chapter.title}): {exc}"
                    )
                )
                continue

            processed_count += 1
            self.stdout.write(
                f"Extracted {concept_count} concept(s) for chapter {chapter.sequence_number}: {chapter.title}"
            )

        action = "Queued" if options["queue"] else "Extracted"
        message = f"{action} missing concept extraction for {processed_count} chapter(s)."
        if failed_count:
            message += f" {failed_count} chapter(s) failed; check the output above."
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(self.style.SUCCESS(message))
