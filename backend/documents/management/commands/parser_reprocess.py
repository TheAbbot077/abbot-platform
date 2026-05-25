from django.core.management.base import BaseCommand, CommandError

from documents.models import Document
from documents.tasks import extract_chapters_from_document
from learning.models import (
    ChapterProgress,
    ConceptLesson,
    ConceptMastery,
    ConceptProgress,
    QuizAttempt,
    ReinforcementRecommendation,
    StudentAIMemory,
    StudentAISpotQuizAttempt,
    TutorMessage,
)


class Command(BaseCommand):
    help = "Safely reprocess a document's chapters after explicit confirmation."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int, help="ID of the document to reprocess.")
        parser.add_argument("--confirm", action="store_true", help="Required. Confirms destructive reprocessing.")
        parser.add_argument(
            "--force-reset-progress",
            action="store_true",
            help="Allow reprocessing even when learning progress exists for this document.",
        )

    def handle(self, *args, **options):
        document = _get_document(options["document_id"])
        if not options["confirm"]:
            raise CommandError(
                "Refusing to reprocess without --confirm. Run parser_preview first and review the proposed chapters."
            )

        progress_summary = _progress_summary(document)
        if _has_progress(progress_summary) and not options["force_reset_progress"]:
            raise CommandError(
                "Learning progress exists for this document. Reprocessing may reset chapters, concepts, quizzes, "
                "lessons, Ariel memory, and recommendations. Re-run with --confirm --force-reset-progress only "
                "after you are sure this reset is intended."
            )

        self.stdout.write(self.style.WARNING("Reprocessing will replace stored chapters and concepts."))
        self.stdout.write(self.style.WARNING("Related learning progress may be reset by cascading deletes."))
        if _has_progress(progress_summary):
            self.stdout.write(self.style.WARNING("Force reset enabled for existing learning progress:"))
            for label, count in progress_summary.items():
                if count:
                    self.stdout.write(f"- {label}: {count}")

        extracted_count = extract_chapters_from_document(document.id)
        self.stdout.write(self.style.SUCCESS(f"Reprocessed document {document.id}. Extracted {extracted_count} chapter(s)."))


def _get_document(document_id: int) -> Document:
    try:
        return Document.objects.get(id=document_id)
    except Document.DoesNotExist as exc:
        raise CommandError(f"Document {document_id} does not exist.") from exc


def _progress_summary(document: Document) -> dict[str, int]:
    concept_filter = {"concept__chapter__document": document}
    return {
        "chapter progress": ChapterProgress.objects.filter(chapter__document=document).count(),
        "concept progress": ConceptProgress.objects.filter(**concept_filter).count(),
        "quiz attempts": QuizAttempt.objects.filter(**concept_filter).count(),
        "concept lessons": ConceptLesson.objects.filter(**concept_filter).count(),
        "tutor messages": TutorMessage.objects.filter(**concept_filter).count(),
        "concept mastery": ConceptMastery.objects.filter(**concept_filter).count(),
        "Ariel memory": StudentAIMemory.objects.filter(**concept_filter).count(),
        "Ariel spot quizzes": StudentAISpotQuizAttempt.objects.filter(**concept_filter).count(),
        "reinforcement recommendations": ReinforcementRecommendation.objects.filter(**concept_filter).count(),
    }


def _has_progress(progress_summary: dict[str, int]) -> bool:
    return any(count > 0 for count in progress_summary.values())
