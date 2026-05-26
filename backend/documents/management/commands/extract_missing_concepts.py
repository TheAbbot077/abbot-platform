from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from documents.models import Chapter, Document, DocumentStatus
from documents.tasks import extract_concepts_from_chapter, _mark_document_ready_if_concepts_are_complete


class Command(BaseCommand):
    help = "Repair chapters whose concepts are missing or not marked teachable."

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
        chapters = (
            Chapter.objects.select_related("document")
            .annotate(
                total_concept_count=Count("concepts", distinct=True),
                required_concept_count=Count("concepts", filter=Q(concepts__is_required=True), distinct=True),
            )
            .filter(Q(total_concept_count=0) | Q(required_concept_count=0))
            .order_by(
                "document_id",
                "sequence_number",
            )
        )
        if options.get("document_id"):
            chapters = chapters.filter(document_id=options["document_id"])
        if options.get("limit"):
            chapters = chapters[: options["limit"]]

        extracted_count = 0
        repaired_required_count = 0
        failed_count = 0
        touched_document_ids = set()

        for chapter in chapters:
            document = chapter.document
            touched_document_ids.add(document.id)
            if document.status != DocumentStatus.PROCESSING_CONCEPTS:
                document.status = DocumentStatus.PROCESSING_CONCEPTS
                document.save(update_fields=["status", "updated_at"])

            if options["queue"]:
                if chapter.total_concept_count == 0:
                    extract_concepts_from_chapter.delay(chapter.id)
                    extracted_count += 1
                else:
                    repaired_required_count += chapter.concepts.update(is_required=True)
                    _mark_document_ready_if_concepts_are_complete(document.id)
                continue

            if chapter.total_concept_count > 0 and chapter.required_concept_count == 0:
                updated = chapter.concepts.update(is_required=True)
                repaired_required_count += updated
                _mark_document_ready_if_concepts_are_complete(document.id)
                self.stdout.write(
                    f"Marked {updated} existing concept(s) required for chapter "
                    f"{chapter.sequence_number}: {chapter.title}"
                )
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

            extracted_count += 1
            self.stdout.write(
                f"Extracted {concept_count} concept(s) for chapter {chapter.sequence_number}: {chapter.title}"
            )

        for document_id in touched_document_ids:
            _mark_document_ready_if_concepts_are_complete(document_id)

        action = "Queued" if options["queue"] else "Extracted"
        message = (
            f"{action} missing concept extraction for {extracted_count} chapter(s). "
            f"Repaired {repaired_required_count} existing concept(s) as required."
        )
        if failed_count:
            message += f" {failed_count} chapter(s) failed; check the output above."
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(self.style.SUCCESS(message))

        if extracted_count == 0 and repaired_required_count == 0:
            self._write_document_summary(options.get("document_id"))

    def _write_document_summary(self, document_id: int | None) -> None:
        documents = Document.objects.all().order_by("-created_at")
        if document_id:
            documents = documents.filter(id=document_id)

        self.stdout.write("No repairable chapters found. Current document learning counts:")
        for document in documents[:10]:
            chapter_count = Chapter.objects.filter(document=document).count()
            total_concepts = document.chapters.aggregate(count=Count("concepts"))["count"] or 0
            required_concepts = document.chapters.aggregate(
                count=Count("concepts", filter=Q(concepts__is_required=True))
            )["count"] or 0
            self.stdout.write(
                f"- Document {document.id}: {document.title} | status={document.status} | "
                f"subject_id={document.subject_id} | chapters={chapter_count} | "
                f"concepts={total_concepts} | required_concepts={required_concepts}"
            )
