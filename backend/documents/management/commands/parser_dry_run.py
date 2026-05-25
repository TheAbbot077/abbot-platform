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
    help = "Preview proposed chapter extraction for a document without modifying stored data."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int, help="ID of the document to inspect.")

    def handle(self, *args, **options):
        document_id = options["document_id"]
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist as exc:
            raise CommandError(f"Document {document_id} does not exist.") from exc

        document_text = extract_text_from_pdf(document.file.path)
        result = detect_ordered_chapters_with_metadata(document_text)
        resolver_result = select_best_chapter_sequence(_chapter_candidates(document_text), full_text=document_text)

        self.stdout.write(f"Document: {document.title} (id={document.id})")
        self.stdout.write(f"Parser strategy: {result.strategy_used}")
        self.stdout.write(f"Confidence score: {result.confidence_score:.2f}")

        self.stdout.write(f"Legacy parser warnings ({len(result.warnings)}):")
        if result.warnings:
            for warning in result.warnings:
                self.stdout.write(f"- {warning}")
        else:
            self.stdout.write("- None")

        self.stdout.write(f"Accepted chapter count: {len(result.accepted_chapters)}")
        self.stdout.write(f"Legacy accepted chapter count: {len(result.accepted_chapters)}")
        self.stdout.write("Legacy accepted chapters:")
        for chapter in result.accepted_chapters:
            preview = _preview(chapter.extracted_text)
            methods = ", ".join(chapter.detection_methods) or "unknown"
            self.stdout.write(
                f"{chapter.sequence_number}. {chapter.title} "
                f"(confidence={chapter.confidence_score:.2f}, methods={methods})"
            )
            self.stdout.write(f"   Preview: {preview}")

        self.stdout.write(f"Resolver confidence: {resolver_result.confidence_score:.2f}")
        self.stdout.write(f"Resolver warnings ({len(resolver_result.warnings)}):")
        if resolver_result.warnings:
            for warning in resolver_result.warnings:
                self.stdout.write(f"- {warning}")
        else:
            self.stdout.write("- None")

        self.stdout.write(f"Resolver proposed chapter count: {len(resolver_result.accepted_chapters)}")
        self.stdout.write("Resolver proposed chapters:")
        for chapter in resolver_result.accepted_chapters:
            preview = _preview(chapter.extracted_text)
            methods = ", ".join(chapter.detection_methods) or "unknown"
            self.stdout.write(
                f"{chapter.sequence_number}. {chapter.title} "
                f"(confidence={chapter.confidence_score:.2f}, methods={methods})"
            )
            self.stdout.write(f"   Preview: {preview}")

        self.stdout.write("Legacy vs resolver differences:")
        differences = _chapter_differences(result.accepted_chapters, resolver_result.accepted_chapters)
        if differences:
            for difference in differences:
                self.stdout.write(f"- {difference}")
        else:
            self.stdout.write("- None")

        self.stdout.write(f"Rejected candidate count: {len(result.rejected_candidates)}")
        self.stdout.write("Rejected candidates:")
        if result.rejected_candidates:
            for candidate in result.rejected_candidates:
                self.stdout.write(
                    f"- {candidate.title} "
                    f"(reason={candidate.reason}, method={candidate.detection_method}, "
                    f"confidence={candidate.confidence_score:.2f})"
                )
                if candidate.evidence:
                    self.stdout.write(f"  Evidence: {_preview(candidate.evidence)}")
        else:
            self.stdout.write("- None")

        self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes were made."))


def _chapter_candidates(text: str):
    candidates = regex_heading_candidates(text)
    candidates.extend(multiline_heading_candidates(text))
    candidates.extend(toc_like_candidates(text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(text))
    return candidates


def _chapter_differences(legacy_chapters, resolver_chapters) -> list[str]:
    differences = []
    if len(legacy_chapters) != len(resolver_chapters):
        differences.append(
            f"chapter count differs: legacy={len(legacy_chapters)}, resolver={len(resolver_chapters)}"
        )

    max_length = max(len(legacy_chapters), len(resolver_chapters))
    for index in range(max_length):
        legacy_title = legacy_chapters[index].title if index < len(legacy_chapters) else "<missing>"
        resolver_title = resolver_chapters[index].title if index < len(resolver_chapters) else "<missing>"
        if legacy_title != resolver_title:
            differences.append(f"chapter {index + 1}: legacy='{legacy_title}' resolver='{resolver_title}'")

    return differences


def _preview(text: str) -> str:
    normalized = " ".join(text.split())
    return normalized[:300]
