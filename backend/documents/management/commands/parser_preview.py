from django.core.management.base import BaseCommand, CommandError

from documents.models import Document
from documents.parsing.chapter_detector import (
    detect_ordered_chapters_with_metadata,
    fallback_single_chapter_candidate,
    multiline_heading_candidates,
    regex_heading_candidates,
    toc_like_candidates,
)
from documents.parsing.chapter_sequence_resolver import select_best_chapter_sequence
from documents.parsing.pdf_text_extractor import extract_text_from_pdf


class Command(BaseCommand):
    help = "Preview current stored chapters and parser proposals without modifying the database."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int, help="ID of the document to inspect.")

    def handle(self, *args, **options):
        document = _get_document(options["document_id"])
        document_text = extract_text_from_pdf(document.file.path)
        legacy_result = detect_ordered_chapters_with_metadata(document_text)
        resolver_result = select_best_chapter_sequence(_chapter_candidates(document_text), full_text=document_text)

        self.stdout.write(f"Document: {document.title} (id={document.id})")
        self.stdout.write("Current stored chapters:")
        stored_chapters = list(document.chapters.order_by("sequence_number"))
        if stored_chapters:
            for chapter in stored_chapters:
                self.stdout.write(f"{chapter.sequence_number}. {chapter.title}")
        else:
            self.stdout.write("- None")

        self.stdout.write(f"Legacy parser proposal ({len(legacy_result.accepted_chapters)} chapters):")
        _write_chapters(self, legacy_result.accepted_chapters)
        self.stdout.write(f"Legacy warnings ({len(legacy_result.warnings)}):")
        _write_warnings(self, legacy_result.warnings)

        self.stdout.write(f"Resolver proposal ({len(resolver_result.accepted_chapters)} chapters):")
        _write_chapters(self, resolver_result.accepted_chapters)
        self.stdout.write(f"Resolver confidence: {resolver_result.confidence_score:.2f}")
        self.stdout.write(f"Resolver warnings ({len(resolver_result.warnings)}):")
        _write_warnings(self, resolver_result.warnings)

        self.stdout.write("Current stored vs legacy proposal differences:")
        differences = _stored_vs_proposed_differences(stored_chapters, legacy_result.accepted_chapters)
        _write_warnings(self, differences)

        self.stdout.write(self.style.SUCCESS("Preview complete. No database changes were made."))


def _get_document(document_id: int) -> Document:
    try:
        return Document.objects.get(id=document_id)
    except Document.DoesNotExist as exc:
        raise CommandError(f"Document {document_id} does not exist.") from exc


def _chapter_candidates(text: str):
    candidates = regex_heading_candidates(text)
    candidates.extend(multiline_heading_candidates(text))
    candidates.extend(toc_like_candidates(text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(text))
    return candidates


def _write_chapters(command: BaseCommand, chapters) -> None:
    if not chapters:
        command.stdout.write("- None")
        return

    for chapter in chapters:
        command.stdout.write(f"{chapter.sequence_number}. {chapter.title}")


def _write_warnings(command: BaseCommand, warnings: list[str]) -> None:
    if not warnings:
        command.stdout.write("- None")
        return

    for warning in warnings:
        command.stdout.write(f"- {warning}")


def _stored_vs_proposed_differences(stored_chapters, proposed_chapters) -> list[str]:
    differences = []
    if len(stored_chapters) != len(proposed_chapters):
        differences.append(f"chapter count differs: stored={len(stored_chapters)}, proposed={len(proposed_chapters)}")

    max_length = max(len(stored_chapters), len(proposed_chapters))
    for index in range(max_length):
        stored_title = stored_chapters[index].title if index < len(stored_chapters) else "<missing>"
        proposed_title = proposed_chapters[index].title if index < len(proposed_chapters) else "<missing>"
        if stored_title != proposed_title:
            differences.append(f"chapter {index + 1}: stored='{stored_title}' proposed='{proposed_title}'")

    return differences
