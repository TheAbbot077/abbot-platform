from pathlib import Path
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from learning.models import ChapterProgress, ConceptProgress, QuizAttempt, ReinforcementRecommendation, StudentAIMemory

from .models import Chapter, Concept, ContentClassification, Document, Subject
from .parsing.literary_toolkit import classify_document_content
from .services import (
    AcceptedChapter,
    ChapterDetectionResult,
    detect_ordered_chapters,
    detect_ordered_chapters_with_metadata,
    detect_ordered_concepts,
    extract_chapter_learning_content,
    fallback_single_chapter_candidate,
    multiline_heading_candidates,
    regex_heading_candidates,
    select_best_chapter_sequence,
    toc_like_candidates,
)
from .tasks import extract_chapters_from_document, extract_concepts_from_chapter


def parser_candidates_for_text(document_text: str):
    candidates = regex_heading_candidates(document_text)
    candidates.extend(multiline_heading_candidates(document_text))
    candidates.extend(toc_like_candidates(document_text))
    if not candidates:
        candidates.extend(fallback_single_chapter_candidate(document_text))
    return candidates


class OrderedStudyContentModelTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="student",
            email="student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Biology Notes",
            file=SimpleUploadedFile("biology.pdf", b"fake pdf content", content_type="application/pdf"),
        )

    def test_chapters_are_returned_by_explicit_sequence_number(self) -> None:
        Chapter.objects.create(document=self.document, title="Second Chapter", sequence_number=2)
        Chapter.objects.create(document=self.document, title="First Chapter", sequence_number=1)

        titles = list(self.document.chapters.values_list("title", flat=True))

        self.assertEqual(titles, ["First Chapter", "Second Chapter"])

    def test_chapter_sequence_number_is_unique_per_document(self) -> None:
        Chapter.objects.create(document=self.document, title="Chapter One", sequence_number=1)

        with self.assertRaises(IntegrityError):
            Chapter.objects.create(document=self.document, title="Duplicate Chapter One", sequence_number=1)

    def test_chapter_sequence_number_must_start_at_one_or_greater(self) -> None:
        with self.assertRaises(IntegrityError):
            Chapter.objects.create(document=self.document, title="Invalid Chapter", sequence_number=0)

    def test_concepts_are_returned_by_explicit_sequence_number(self) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Cells", sequence_number=1)
        Concept.objects.create(chapter=chapter, title="Cell Membrane", sequence_number=2)
        Concept.objects.create(chapter=chapter, title="Cell Theory", sequence_number=1)

        titles = list(chapter.concepts.values_list("title", flat=True))

        self.assertEqual(titles, ["Cell Theory", "Cell Membrane"])

    def test_concept_sequence_number_is_unique_per_chapter(self) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Cells", sequence_number=1)
        Concept.objects.create(chapter=chapter, title="Cell Theory", sequence_number=1)

        with self.assertRaises(IntegrityError):
            Concept.objects.create(chapter=chapter, title="Duplicate Cell Theory", sequence_number=1)

    def test_concept_title_is_unique_per_chapter(self) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Cells", sequence_number=1)
        Concept.objects.create(chapter=chapter, title="Cell Theory", sequence_number=1)

        with self.assertRaises(IntegrityError):
            Concept.objects.create(chapter=chapter, title="cell theory", sequence_number=2)

    def test_concept_is_required_by_default(self) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Cells", sequence_number=1)
        concept = Concept.objects.create(chapter=chapter, title="Cell Theory", sequence_number=1)

        self.assertTrue(concept.is_required)

    def test_concept_sequence_number_must_start_at_one_or_greater(self) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Cells", sequence_number=1)

        with self.assertRaises(IntegrityError):
            Concept.objects.create(chapter=chapter, title="Invalid Concept", sequence_number=0)


class ChapterDetectionTests(TestCase):
    def test_regex_heading_candidates_return_chapter_candidates(self) -> None:
        candidates = regex_heading_candidates("Chapter 1: Basics\nBody")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Chapter 1: Basics")
        self.assertEqual(candidates[0].sequence_number, 1)
        self.assertEqual(candidates[0].detection_method, "regex_heading")
        self.assertGreater(candidates[0].confidence_score, 0)

    def test_multiline_heading_candidates_return_chapter_candidates(self) -> None:
        candidates = multiline_heading_candidates("CHAPTER\n2\nAdvanced Topic\nLearning Objectives")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "CHAPTER 2: Advanced Topic")
        self.assertEqual(candidates[0].sequence_number, 2)
        self.assertEqual(candidates[0].detection_method, "multiline_heading")

    def test_toc_like_candidates_return_low_confidence_chapter_candidates(self) -> None:
        candidates = toc_like_candidates("Chapter 3: Cells . . . . . 42")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Chapter 3: Cells")
        self.assertEqual(candidates[0].sequence_number, 3)
        self.assertEqual(candidates[0].detection_method, "toc_like")
        self.assertLess(candidates[0].confidence_score, 0.5)

    def test_fallback_single_chapter_candidate_returns_one_candidate_for_text(self) -> None:
        candidates = fallback_single_chapter_candidate("Loose notes without headings.")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Chapter 1")
        self.assertEqual(candidates[0].sequence_number, 1)
        self.assertEqual(candidates[0].detection_method, "fallback_single_chapter")

    def test_shadow_resolver_prefers_body_chapters_over_toc_rows(self) -> None:
        document_text = """
        Contents
        Chapter 1: Cells . . . . . 9
        Chapter 2: Ecosystems . . . . . 27

        Chapter 1: Cells
        Cells are the basic unit of life.

        Chapter 2: Ecosystems
        Ecosystems include organisms and their environments.
        """
        candidates = regex_heading_candidates(document_text)
        candidates.extend(toc_like_candidates(document_text))

        result = select_best_chapter_sequence(candidates, full_text=document_text)

        self.assertEqual([chapter.title for chapter in result.accepted_chapters], ["Chapter 1: Cells", "Chapter 2: Ecosystems"])
        self.assertEqual([chapter.sequence_number for chapter in result.accepted_chapters], [1, 2])
        self.assertTrue(any("Cells" in candidate.title for candidate in result.rejected_candidates))

    def test_shadow_resolver_groups_duplicate_strategy_candidates(self) -> None:
        document_text = "Chapter 1: Cells . . . . . 9\nChapter 1: Cells\nBody text."
        candidates = regex_heading_candidates(document_text)
        candidates.extend(toc_like_candidates(document_text))

        result = select_best_chapter_sequence(candidates, full_text=document_text)

        self.assertEqual(len(result.accepted_chapters), 1)
        self.assertEqual(result.accepted_chapters[0].title, "Chapter 1: Cells")

    def test_shadow_resolver_warns_about_fragmented_sequences(self) -> None:
        document_text = """
        Chapter 1: A
        tiny
        Chapter 2: B
        tiny
        Chapter 3: C
        tiny
        """
        result = select_best_chapter_sequence(regex_heading_candidates(document_text), full_text=document_text)

        self.assertTrue(any("fragmented" in warning for warning in result.warnings))
        self.assertLess(result.confidence_score, 1.0)

    def test_detected_chapters_keep_text_order(self) -> None:
        document_text = """
        Chapter 13: Late Topic
        This chapter appears first in the uploaded text.

        Chapter 1: Early Topic
        This chapter appears second in the uploaded text.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual([chapter.title for chapter in chapters], ["Chapter 13: Late Topic", "Chapter 1: Early Topic"])

    def test_detected_chapters_metadata_preserves_compatibility_order(self) -> None:
        document_text = """
        Chapter 1: Basics
        This chapter appears first.

        Chapter 2: Advanced
        This chapter appears second.
        """

        result = detect_ordered_chapters_with_metadata(document_text)
        chapters = detect_ordered_chapters(document_text)

        self.assertIsInstance(result, ChapterDetectionResult)
        self.assertEqual([chapter.title for chapter in chapters], ["Chapter 1: Basics", "Chapter 2: Advanced"])
        self.assertEqual(
            [chapter.title for chapter in result.accepted_chapters],
            ["Chapter 1: Basics", "Chapter 2: Advanced"],
        )
        self.assertEqual([chapter.sequence_number for chapter in result.accepted_chapters], [1, 2])
        self.assertEqual(result.strategy_used, "one_line_chapter_heading")
        self.assertGreater(result.confidence_score, 0)

    def test_detected_chapters_support_written_chapter_numbers(self) -> None:
        document_text = """
        CHAPTER ONE ............................................................................................................................................ 1

        CHAPTER ONE
        Introduction to economics.

        CHAPTER TWO
        Demand and supply.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual([chapter.title for chapter in chapters], ["CHAPTER ONE", "CHAPTER TWO"])

    def test_detected_chapters_ignore_repeated_pdf_page_headers(self) -> None:
        document_text = """
        Chapter 1: | Introduction to Biology 1
        Chapter 1: The Study of Life  .  .  .  .  .  .  .  .  . 9
        Chapter 2: | Cells and Systems 27

        CHAPTER 1
        Introduction to Biology
        1.1 What is biology?
        Biology studies living things.

        Chapter 1: | Introduction to Biology 2
        1.2 Scientific method
        Science uses evidence.

        CHAPTER 2
        Cells and Systems
        2.1 Cell structure
        Cells have organelles.

        Chapter 2: | Cells and Systems 28
        More page text.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual([chapter.title for chapter in chapters], ["CHAPTER 1: The Study of Life", "CHAPTER 2"])
        self.assertIn("1.1 What is biology?", chapters[0].text)
        self.assertIn("1.2 Scientific method", chapters[0].text)
        self.assertIn("2.1 Cell structure", chapters[1].text)

    def test_detected_chapters_can_use_cleaned_page_headers_when_needed(self) -> None:
        document_text = """
        Chapter 1: The Study of Life  .  .  .  .  .  .  .  .  . 9
        Chapter 2: Cells and Systems  .  .  .  .  .  .  .  .  . 27

        Chapter 1: | The Study of Life 9
        1.1 The Science of Biology
        Biology is the study of life.

        Chapter 1: | The Study of Life 10
        1.2 Themes in Biology
        Biology has recurring themes.

        Chapter 2: | Cells and Systems 27
        2.1 Cell Structure
        Cells contain organelles.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual([chapter.title for chapter in chapters], ["Chapter 1: The Study of Life", "Chapter 2: Cells and Systems"])
        self.assertIn("1.1 The Science of Biology", chapters[0].text)
        self.assertIn("1.2 Themes in Biology", chapters[0].text)
        self.assertIn("2.1 Cell Structure", chapters[1].text)

    def test_detected_chapters_use_full_toc_titles_without_creating_toc_chapters(self) -> None:
        document_text = """
        Chapter 65: -The Place of Reward as a Motive in Service . 298
        Chapter 66: -Treasure in Heaven . . . . . 301

        Chapter 65: -The Place of Reward as a Motive in
        Service begins here.

        Chapter 66: -Treasure in Heaven [342]
        Next chapter begins here.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual(
            [chapter.title for chapter in chapters],
            [
                "Chapter 65: The Place of Reward as a Motive in Service",
                "Chapter 66: Treasure in Heaven",
            ],
        )

    def test_detected_chapters_prefer_multiline_chapter_starts_over_toc_and_references(self) -> None:
        document_text = """
        Contents
        Chapter 1      Introduction: The Environment at Risk
        Learning Objectives
        References
        Chapter 2      Environmental Epidemiology
        Learning Objectives
        References

        CHAPTER
        1
        Introduction: The Environment at Risk
        Learning Objectives
        This is the first real chapter body.
        Chapter
        2
        will introduce the next topic later.

        CHAPTER
        2
        Environmental
        Epidemiology
        Learning Objectives
        This is the second real chapter body.
        Chapter 1 has provided background.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual(
            [chapter.title for chapter in chapters],
            ["CHAPTER 1: Introduction: The Environment at Risk", "CHAPTER 2: Environmental Epidemiology"],
        )
        self.assertIn("first real chapter body", chapters[0].text)
        self.assertIn("second real chapter body", chapters[1].text)

    def test_detected_chapters_collapse_duplicate_chapter_numbers(self) -> None:
        document_text = """
        CHAPTER 38
        Conservation Biology and Biodiversity
        Conservation biology protects species and ecosystems.

        Chapter 38: | Conservation Biology and Biodiversity 1771
        Running page header text should remain inside the chapter body.

        Chapter 38: | Conservation Biology and Biodiversity 1772
        More body text.
        """

        chapters = detect_ordered_chapters(document_text)

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "CHAPTER 38")
        self.assertIn("Running page header text", chapters[0].text)

    def test_document_without_headings_becomes_single_chapter(self) -> None:
        chapters = detect_ordered_chapters("One continuous set of notes.")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "Chapter 1")


class ParserRegressionFixtureTests(TestCase):
    def compare_legacy_and_resolver(self, document_text: str):
        legacy_chapters = detect_ordered_chapters(document_text)
        resolver_result = select_best_chapter_sequence(
            parser_candidates_for_text(document_text),
            full_text=document_text,
        )

        self.assertEqual(
            [chapter.sequence_number for chapter in resolver_result.accepted_chapters],
            list(range(1, len(resolver_result.accepted_chapters) + 1)),
        )
        return legacy_chapters, resolver_result

    def test_normal_numbered_chapters_fixture(self) -> None:
        document_text = """
        Chapter 1: Foundations
        This chapter introduces the main ideas.

        Chapter 2: Practice
        This chapter applies the main ideas.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual([chapter.title for chapter in legacy_chapters], ["Chapter 1: Foundations", "Chapter 2: Practice"])
        self.assertEqual(
            [chapter.title for chapter in resolver_result.accepted_chapters],
            ["Chapter 1: Foundations", "Chapter 2: Practice"],
        )

    def test_roman_numeral_chapters_fixture_documents_current_fallback(self) -> None:
        document_text = """
        Chapter I: Origins
        This chapter uses a Roman numeral.

        Chapter II: Growth
        This chapter also uses a Roman numeral.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual([chapter.title for chapter in legacy_chapters], ["Chapter 1"])
        self.assertEqual([chapter.title for chapter in resolver_result.accepted_chapters], ["Chapter 1"])
        self.assertEqual(resolver_result.strategy_used, "shadow_best_sequence_resolver")

    def test_toc_heavy_document_fixture(self) -> None:
        document_text = """
        Contents
        Chapter 1: Cells . . . . . 9
        Chapter 2: Ecosystems . . . . . 27

        Chapter 1: Cells
        Cells are the basic unit of life.

        Chapter 2: Ecosystems
        Ecosystems include organisms and their environments.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual([chapter.title for chapter in legacy_chapters], ["Chapter 1: Cells", "Chapter 2: Ecosystems"])
        self.assertEqual(
            [chapter.title for chapter in resolver_result.accepted_chapters],
            ["Chapter 1: Cells", "Chapter 2: Ecosystems"],
        )
        self.assertGreaterEqual(len(resolver_result.rejected_candidates), 1)

    def test_repeated_page_headers_fixture(self) -> None:
        document_text = """
        Chapter 1: | The Study of Life 1

        CHAPTER 1
        The Study of Life
        Biology studies living things.

        Chapter 1: | The Study of Life 2
        More page body from chapter one.

        CHAPTER 2
        Cells and Systems
        Cells contain organelles.

        Chapter 2: | Cells and Systems 28
        More page body from chapter two.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual([chapter.title for chapter in legacy_chapters], ["CHAPTER 1", "CHAPTER 2"])
        self.assertEqual([chapter.title for chapter in resolver_result.accepted_chapters], ["CHAPTER 1", "CHAPTER 2"])
        self.assertIn("The Study of Life", resolver_result.accepted_chapters[0].extracted_text)
        self.assertIn("Cells and Systems", resolver_result.accepted_chapters[1].extracted_text)

    def test_subsection_heavy_document_fixture(self) -> None:
        document_text = """
        Chapter 1: Economics as a Social Science
        1.1 Scarcity
        Scarcity means wants exceed available resources.
        1.2 Opportunity Cost
        Opportunity cost is the next best alternative.

        Chapter 2: Demand and Supply
        2.1 Demand
        Demand is the willingness and ability to buy.
        2.2 Supply
        Supply is the willingness and ability to sell.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual(len(legacy_chapters), 2)
        self.assertEqual(len(resolver_result.accepted_chapters), 2)
        self.assertIn("1.1 Scarcity", resolver_result.accepted_chapters[0].extracted_text)
        self.assertIn("2.1 Demand", resolver_result.accepted_chapters[1].extracted_text)

    def test_no_clear_chapters_fixture(self) -> None:
        document_text = """
        These notes discuss photosynthesis, cellular respiration, and ecology.
        They are useful, but they do not contain explicit chapter headings.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual([chapter.title for chapter in legacy_chapters], ["Chapter 1"])
        self.assertEqual([chapter.title for chapter in resolver_result.accepted_chapters], ["Chapter 1"])
        self.assertEqual(len(resolver_result.accepted_chapters), 1)

    def test_multiline_chapter_headings_fixture(self) -> None:
        document_text = """
        CHAPTER
        1
        Introduction to Biology
        Biology studies life.

        CHAPTER
        2
        Cells and Systems
        Cells have structures and functions.
        """

        legacy_chapters, resolver_result = self.compare_legacy_and_resolver(document_text)

        self.assertEqual(
            [chapter.title for chapter in legacy_chapters],
            ["CHAPTER 1: Introduction to Biology", "CHAPTER 2: Cells and Systems"],
        )
        self.assertEqual(
            [chapter.title for chapter in resolver_result.accepted_chapters],
            ["CHAPTER 1: Introduction to Biology", "CHAPTER 2: Cells and Systems"],
        )
        self.assertTrue(
            all("multiline_heading" in chapter.detection_methods for chapter in resolver_result.accepted_chapters)
        )


class ParserWarningTests(TestCase):
    def test_warns_when_only_one_chapter_detected_in_long_document(self) -> None:
        document_text = "Long study notes. " * 2_200

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("Only one chapter" in warning for warning in result.warnings))

    def test_warns_when_too_many_chapters_are_detected(self) -> None:
        document_text = "\n".join(
            f"Chapter {index}: Topic {index}\nBody for topic {index}."
            for index in range(1, 122)
        )

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("chapters were detected" in warning for warning in result.warnings))

    def test_warns_about_repeated_duplicate_chapter_numbers(self) -> None:
        document_text = """
        CHAPTER 1
        Real first chapter.

        Chapter 1: | Real first chapter 2
        Repeated page header.

        Chapter 1: | Real first chapter 3
        Repeated page header.
        """

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("Repeated duplicate chapter numbers" in warning for warning in result.warnings))

    def test_warns_about_large_gaps_between_detected_chapters(self) -> None:
        document_text = f"""
        Chapter 1: Short
        Brief intro.

        Chapter 2: Very Long
        {"Long body. " * 1_000}

        Chapter 3: Short Again
        Brief ending.
        """

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("Large gaps" in warning for warning in result.warnings))

    def test_warns_about_suspiciously_short_chapters(self) -> None:
        document_text = """
        Chapter 1: A
        Tiny.
        Chapter 2: B
        Tiny.
        Chapter 3: C
        Tiny.
        """

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("suspiciously short" in warning for warning in result.warnings))

    def test_warns_about_toc_candidates_without_matching_body_chapters(self) -> None:
        document_text = """
        Contents
        Chapter 1: Cells . . . . . 9
        Chapter 2: Ecosystems . . . . . 27
        Appendix and glossary follow.
        """

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("TOC-like chapter candidates" in warning for warning in result.warnings))

    def test_warns_when_legacy_and_resolver_disagree_significantly(self) -> None:
        document_text = """
        Chapter 3: Later Topic
        This appears first.

        Chapter 1: Early Topic
        This appears second.

        Chapter 2: Middle Topic
        This appears third.
        """

        result = detect_ordered_chapters_with_metadata(document_text)

        self.assertTrue(any("disagree significantly" in warning for warning in result.warnings))

    def test_warns_when_resolver_confidence_is_low(self) -> None:
        result = detect_ordered_chapters_with_metadata("Loose notes without chapter headings.")

        self.assertTrue(any("Shadow resolver confidence is low" in warning for warning in result.warnings))


class ConceptExtractionTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="concept-student",
            email="concept-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Physics Notes",
            file=SimpleUploadedFile("physics.pdf", b"fake pdf content", content_type="application/pdf"),
        )

    def test_detected_concepts_keep_chapter_content_order(self) -> None:
        chapter_text = """
        Chapter 1: Motion
        - Velocity
        - Acceleration
        Force: A push or pull on an object.
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual([concept.title for concept in concepts], ["Velocity", "Acceleration", "Force"])

    def test_detected_concepts_skip_duplicates_within_chapter(self) -> None:
        chapter_text = """
        - Velocity
        - velocity
        - Acceleration
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual([concept.title for concept in concepts], ["Velocity", "Acceleration"])

    def test_chapter_objectives_are_metadata_not_teachable_concepts(self) -> None:
        chapter_text = """
        Chapter 1: Economics
        After successful completion of this chapter, you will be able to
        1. Understand the concept and nature of economics
        2. Analyze how resources are efficiently used to produce output

        1.1 Scarcity
        Scarcity: Unlimited wants compete for limited resources.
        Opportunity Cost: The value of the next best alternative.
        """

        learning_content = extract_chapter_learning_content("Chapter 1: Economics", chapter_text)

        self.assertEqual(
            learning_content.chapter_objectives,
            [
                "Understand the concept and nature of economics",
                "Analyze how resources are efficiently used to produce output",
            ],
        )
        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            ["Scarcity", "Opportunity Cost"],
        )

    def test_arrow_bulleted_objectives_are_not_teachable_concepts(self) -> None:
        chapter_text = """
        Chapter objectives
        After successful completion of this chapter, you will be able to:
         understand the concept and nature of economics;
         analyze how resources are efficiently used in producing output;

        1.1 Definition of economics
        Economics: A social science about allocating scarce resources.
        Example:
        """

        learning_content = extract_chapter_learning_content("Chapter 1", chapter_text)

        self.assertEqual(
            learning_content.chapter_objectives,
            [
                "understand the concept and nature of economics",
                "analyze how resources are efficiently used in producing output",
            ],
        )
        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            ["Definition of economics", "Economics"],
        )

    def test_tabbed_learning_objectives_and_study_sections_are_not_concepts(self) -> None:
        chapter_text = """
        CHAPTER
        1
        Introduction
        L
        EARNING
        O
        BJECTIVES
        State a definition of the term environmental health.
        Describe current issues in the environmental health field.
        List at least five major events in the history of
        environmental health.
        INTRODUCTION
        Environmental health: The study of environmental factors that affect health.
        Population dynamics: Patterns in population change.
        STUDY\tQUESTIONS\tAND\tEXERCISES
        Define the following terms.
        REFERENCES
        Source:
        Available at:
        """

        learning_content = extract_chapter_learning_content("Chapter 1: Introduction", chapter_text)

        self.assertEqual(
            learning_content.chapter_objectives,
            [
                "State a definition of the term environmental health",
                "Describe current issues in the environmental health field",
                "List at least five major events in the history of environmental health",
            ],
        )
        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            ["Environmental health", "Population dynamics"],
        )

    def test_detected_concepts_reject_rough_textbook_fragments(self) -> None:
        chapter_text = """
        1.1 Definition of economics
        is because different economists defined economics from different perspectives:
        a. Wealth definition,
        b. Welfare definition,
        c. Scarcity definition, and
        d. Growth definition
        Are demand and want similar? Why?
        other things remaining the same. A typical demand function is given by:
        2.3 Demand schedule, demand curve and demand function
        Law of demand: Price and quantity demanded move in opposite directions.
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual(
            [concept.title for concept in concepts],
            [
                "Definition of economics",
                "Demand schedule, demand curve and demand function",
                "Law of demand",
            ],
        )

    def test_concept_extraction_ignores_end_of_chapter_assessments(self) -> None:
        chapter_text = """
        1.1 Science of Biology
        Discovery science:
        Hypothesis: A testable explanation.

        REVIEW QUESTIONS
        1. What is a suggested and testable explanation for an event called?
        a. discovery
        b. hypothesis
        c. scientific method
        d. theory

        CRITICAL THINKING QUESTIONS
        12. Is mathematics a natural science? Explain your reasoning.
        """

        learning_content = extract_chapter_learning_content("Chapter 1", chapter_text)

        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            ["Science of Biology", "Discovery science", "Hypothesis"],
        )

    def test_chapter_title_becomes_fallback_concept_when_body_has_no_headings(self) -> None:
        chapter_text = """
        Chapter 1: —Coworkers With God
        God invites people to cooperate in generous service.
        """

        learning_content = extract_chapter_learning_content("Chapter 1: —Coworkers With God", chapter_text)

        self.assertEqual([concept.title for concept in learning_content.teachable_concepts], ["Coworkers With God"])

    def test_literary_material_uses_literary_toolkit_units(self) -> None:
        chapter_text = """
        Chapter 1: The Night Visitor
        "I will not go," Mara said, looking toward the dark road.
        Her brother replied, "Then we wait until morning."
        The setting is a lonely village at night, and the conflict grows as
        the stranger arrives. The symbol of the broken lantern returns twice.
        This chapter uses imagery, tone, foreshadowing, dialogue, and theme.
        """

        learning_content = extract_chapter_learning_content("Chapter 1: The Night Visitor", chapter_text)

        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            [
                "Chapter summary",
                "Key events",
                "Character development",
                "Conflict and tension",
                "Themes and ideas",
                "Symbols and literary devices",
                "Important quotations",
                "Interpretation questions",
            ],
        )
        self.assertTrue(
            all(concept.summary.startswith("[Literary Toolkit]") for concept in learning_content.teachable_concepts)
        )

    def test_literature_textbook_extracts_literary_analysis_units(self) -> None:
        chapter_text = """
        Literary Devices
        A metaphor compares two things directly.
        Imagery uses sensory language.
        Tone is the author's attitude.
        In analysis, identify the device, cite the example, and explain meaning.
        """

        learning_content = extract_chapter_learning_content("Chapter 2: Literary Devices", chapter_text)

        self.assertEqual(
            [concept.title for concept in learning_content.teachable_concepts],
            ["Literary terms in this section", "How the examples work", "Interpretation practice"],
        )

    def test_document_content_classification_detects_literary_types(self) -> None:
        poem_text = "A poetry collection with stanzas, verse, imagery, metaphor, tone, and speaker."
        play_text = "ACT I\nSCENE I\nStage direction: Enter Mara.\nMARA: We must go."
        literature_textbook = "Literary devices include metaphor, simile, imagery, tone, theme, and analysis examples."

        self.assertEqual(classify_document_content("Poems", poem_text), ContentClassification.POEM)
        self.assertEqual(classify_document_content("A Play", play_text), ContentClassification.PLAY)
        self.assertEqual(
            classify_document_content("Language Arts", literature_textbook),
            ContentClassification.LITERATURE_TEXTBOOK,
        )

    def test_literary_learning_content_stores_schema_metadata(self) -> None:
        chapter_text = """
        Chapter 1: The Night Visitor
        "I will not go," Mara said.
        The setting is a lonely village at night, and the symbol of the broken lantern returns.
        This chapter uses imagery, tone, foreshadowing, dialogue, and theme.
        """

        learning_content = extract_chapter_learning_content(
            "Chapter 1: The Night Visitor",
            chapter_text,
            ContentClassification.NOVEL,
            section_sequence=3,
        )

        metadata = learning_content.literary_metadata
        self.assertEqual(learning_content.content_classification, ContentClassification.NOVEL)
        self.assertEqual(metadata["section_sequence"], 3)
        self.assertIn("summary", metadata)
        self.assertIn("key_events", metadata)
        self.assertIn("characters_present", metadata)
        self.assertIn("character_development", metadata)
        self.assertIn("themes", metadata)
        self.assertIn("symbols", metadata)
        self.assertIn("literary_devices", metadata)
        self.assertIn("important_quotes", metadata)
        self.assertIn("vocabulary", metadata)
        self.assertIn("interpretation_questions", metadata)

    def test_detected_concepts_reject_answer_choices_and_sentence_fragments(self) -> None:
        chapter_text = """
        1.1 Science of Biology
        | Themes and Concepts of Biology
        From its earliest beginnings, biology has wrestled with three questions
        All living organisms share several key characteristics or functions
        An armadillo
        A camel
        According to a table in the chapter
        Available at
        Definition of terms used in the table
        Both astronomy and astrology study the stars
        Scientific method: A structured process for asking and testing questions.
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual([concept.title for concept in concepts], ["Science of Biology", "Scientific method"])

    def test_detected_concepts_reject_table_formula_and_exercise_artifacts(self) -> None:
        chapter_text = """
        2.1 Theory of demand
        Consumer-1 Consumer - 2 Consumer:
        Numerical Example:
        Q:
        D:
        MU1/P1 = MU2/P2:
        Proof:
        Solution:
        Note that:
        If:
        Part I:
        Symbolically, the formula may be expressed thus:
        Calculate the market equilibrium price and quantity:
        Find the utility maximizing quantities of good X and Y:
        Draw the budget line:
        At equilibrium, Qd= Qs:
        At point E market:
        If demand and supply change in the opposite directions:
        Express the budget constraint as:
        3.4 The budget line or the price line
        Budget line: A line showing affordable combinations of goods.
        Law of demand: Price and quantity demanded move in opposite directions.
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual(
            [concept.title for concept in concepts],
            [
                "Theory of demand",
                "Budget line or the price line",
                "Budget line",
                "Law of demand",
            ],
        )

    def test_detected_concepts_normalize_lightweight_textbook_headings(self) -> None:
        chapter_text = """
        The law of supply:
        The ordinal utility theory:
        Major steps in the deductive approach include:
        The PPF describes three important concepts:
        Determine cross price elasticity:
        Identify different decision making units:
        iv) The importance of the commodity in the consumers' budget:
        Case of one commodity:
        Case of two or more commodities:
        """

        concepts = detect_ordered_concepts(chapter_text)

        self.assertEqual(
            [concept.title for concept in concepts],
            [
                "Law of supply",
                "Ordinal utility theory",
                "Deductive approach steps",
                "PPF concepts",
                "Cross price elasticity",
                "Different decision making units",
                "Importance of the commodity in the consumers' budget",
                "One commodity case",
                "Two or more commodities case",
            ],
        )

    def test_concept_extraction_task_writes_required_ordered_concepts(self) -> None:
        chapter = Chapter.objects.create(
            document=self.document,
            title="Motion",
            sequence_number=1,
            extracted_text="- Velocity\n- Acceleration",
        )

        extracted_count = extract_concepts_from_chapter(chapter.id)

        self.assertEqual(extracted_count, 2)
        concepts = list(chapter.concepts.values_list("title", "sequence_number", "is_required"))
        self.assertEqual(concepts, [("Velocity", 1, True), ("Acceleration", 2, True)])

    def test_concept_extraction_task_saves_objectives_without_creating_concepts(self) -> None:
        chapter = Chapter.objects.create(
            document=self.document,
            title="Economics",
            sequence_number=1,
            extracted_text="""
            After successful completion of this chapter, you will be able to
            1. Understand the concept and nature of economics
            2. Analyze how resources are efficiently used

            Scarcity: Unlimited wants compete for limited resources.
            Opportunity Cost: The value of the next best alternative.
            """,
        )

        extracted_count = extract_concepts_from_chapter(chapter.id)

        chapter.refresh_from_db()
        self.assertEqual(extracted_count, 2)
        self.assertEqual(
            chapter.chapter_objectives,
            [
                "Understand the concept and nature of economics",
                "Analyze how resources are efficiently used",
            ],
        )
        self.assertEqual(list(chapter.concepts.values_list("title", flat=True)), ["Scarcity", "Opportunity Cost"])

    def test_concept_extraction_task_saves_literary_metadata(self) -> None:
        self.document.content_classification = ContentClassification.NOVEL
        self.document.save(update_fields=["content_classification"])
        chapter = Chapter.objects.create(
            document=self.document,
            title="Chapter 1: The Night Visitor",
            sequence_number=1,
            extracted_text="""
            "I will not go," Mara said, looking toward the dark road.
            The conflict grows as the stranger arrives.
            The broken lantern is a symbol, and the chapter uses imagery, tone, and theme.
            """,
        )

        extracted_count = extract_concepts_from_chapter(chapter.id)

        chapter.refresh_from_db()
        self.assertGreater(extracted_count, 0)
        self.assertEqual(chapter.literary_metadata["content_classification"], ContentClassification.NOVEL)
        self.assertEqual(chapter.literary_metadata["section_sequence"], 1)
        self.assertIn("interpretation_questions", chapter.literary_metadata)
        self.assertIn("Chapter summary", list(chapter.concepts.values_list("title", flat=True)))

    def test_concept_extraction_task_replaces_existing_concepts(self) -> None:
        chapter = Chapter.objects.create(
            document=self.document,
            title="Motion",
            sequence_number=1,
            extracted_text="- Velocity",
        )
        Concept.objects.create(chapter=chapter, title="Old Concept", sequence_number=1)

        extract_concepts_from_chapter(chapter.id)

        self.assertEqual(list(chapter.concepts.values_list("title", flat=True)), ["Velocity"])

    def test_concept_extraction_marks_document_ready_when_all_chapters_have_concepts(self) -> None:
        first_chapter = Chapter.objects.create(
            document=self.document,
            title="Motion",
            sequence_number=1,
            extracted_text="- Velocity",
        )
        second_chapter = Chapter.objects.create(
            document=self.document,
            title="Forces",
            sequence_number=2,
            extracted_text="- Force",
        )

        extract_concepts_from_chapter(first_chapter.id)
        self.document.refresh_from_db()
        self.assertNotEqual(self.document.status, "ready")

        extract_concepts_from_chapter(second_chapter.id)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, "ready")

    def test_extract_missing_concepts_command_can_run_synchronously(self) -> None:
        self.document.status = "ready"
        self.document.save(update_fields=["status"])
        Chapter.objects.create(
            document=self.document,
            title="Motion",
            sequence_number=1,
            extracted_text="- Velocity",
        )

        output = StringIO()
        call_command("extract_missing_concepts", "--document-id", str(self.document.id), stdout=output)

        self.document.refresh_from_db()
        self.assertIn("Extracted 1 concept(s)", output.getvalue())
        self.assertEqual(list(Concept.objects.values_list("title", flat=True)), ["Velocity"])
        self.assertEqual(self.document.status, "ready")

    def test_extract_missing_concepts_command_repairs_non_required_concepts(self) -> None:
        chapter = Chapter.objects.create(
            document=self.document,
            title="Motion",
            sequence_number=1,
            extracted_text="- Velocity",
        )
        concept = Concept.objects.create(chapter=chapter, title="Velocity", sequence_number=1, is_required=False)

        output = StringIO()
        call_command("extract_missing_concepts", "--document-id", str(self.document.id), stdout=output)

        concept.refresh_from_db()
        self.assertTrue(concept.is_required)
        self.assertIn("Marked 1 existing concept(s) required", output.getvalue())


class DocumentUploadApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="uploader",
            email="uploader@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @override_settings(MEDIA_ROOT="/tmp/study-management-test-media")
    @patch("documents.views.extract_chapters_from_document.delay")
    def test_upload_pdf_creates_document_and_schedules_extraction(self, mock_delay) -> None:
        upload = SimpleUploadedFile("notes.pdf", b"%PDF-1.4 fake content", content_type="application/pdf")

        response = self.client.post(reverse("document-list"), {"title": "Notes", "file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(owner=self.user, title="Notes")
        mock_delay.assert_called_once_with(document.id)
        self.assertEqual(document.status, "uploaded")

    @patch("documents.views.extract_chapters_from_document.delay")
    def test_upload_rejects_non_pdf_files(self, mock_delay) -> None:
        upload = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")

        response = self.client.post(reverse("document-list"), {"title": "Notes", "file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_delay.assert_not_called()

    @override_settings(MEDIA_ROOT="/tmp/study-management-delete-test-media")
    def test_delete_document_removes_file_and_related_learning_records(self) -> None:
        document = Document.objects.create(
            owner=self.user,
            title="Delete Me",
            file=SimpleUploadedFile("delete-me.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"),
        )
        chapter = Chapter.objects.create(document=document, title="Chapter", sequence_number=1)
        concept = Concept.objects.create(chapter=chapter, title="Concept", sequence_number=1)
        ConceptProgress.objects.create(user=self.user, concept=concept)
        QuizAttempt.objects.create(
            user=self.user,
            concept=concept,
            submitted_answers={},
            total_questions=1,
            correct_answers=0,
            score=0,
            passed=False,
        )
        StudentAIMemory.objects.create(
            user=self.user,
            concept=concept,
            taught_content="Taught content",
            taught_at=timezone.now(),
            initial_mastery_score=50,
            current_retention_score=50,
        )
        ReinforcementRecommendation.objects.create(
            user=self.user,
            concept=concept,
            reason="Practice this again.",
            student_ai_score=40,
            recommended_action="Teach Ariel",
        )
        file_path = Path(document.file.path)
        self.assertTrue(file_path.exists())

        response = self.client.delete(reverse("document-detail", kwargs={"pk": document.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=document.id).exists())
        self.assertFalse(Chapter.objects.filter(id=chapter.id).exists())
        self.assertFalse(Concept.objects.filter(id=concept.id).exists())
        self.assertFalse(QuizAttempt.objects.filter(user=self.user, concept_id=concept.id).exists())
        self.assertFalse(ConceptProgress.objects.filter(user=self.user, concept_id=concept.id).exists())
        self.assertFalse(StudentAIMemory.objects.filter(user=self.user, concept_id=concept.id).exists())
        self.assertFalse(ReinforcementRecommendation.objects.filter(user=self.user, concept_id=concept.id).exists())
        self.assertFalse(file_path.exists())

    def test_cannot_delete_another_users_document(self) -> None:
        other_user = get_user_model().objects.create_user(username="other-delete-user")
        other_document = Document.objects.create(
            owner=other_user,
            title="Private",
            file=SimpleUploadedFile("private.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"),
        )

        response = self.client.delete(reverse("document-detail", kwargs={"pk": other_document.id}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Document.objects.filter(id=other_document.id).exists())

    def test_delete_subject_is_blocked_when_it_has_textbooks(self) -> None:
        subject = Subject.objects.create(owner=self.user, name="Economics")
        Document.objects.create(
            owner=self.user,
            subject=subject,
            title="Economics Textbook",
            file=SimpleUploadedFile("economics.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"),
        )

        response = self.client.delete(reverse("subject-detail", kwargs={"pk": subject.id}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Delete or move", response.data["detail"])
        self.assertTrue(Subject.objects.filter(id=subject.id).exists())

    def test_delete_empty_subject(self) -> None:
        subject = Subject.objects.create(owner=self.user, name="Biology")

        response = self.client.delete(reverse("subject-detail", kwargs={"pk": subject.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subject.objects.filter(id=subject.id).exists())


class SubjectApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="subject-owner",
            email="subject-owner@example.com",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-subject-owner",
            email="other-subject-owner@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_subject_for_current_user(self) -> None:
        response = self.client.post(reverse("subject-list"), {"name": "Economics"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Economics")
        self.assertTrue(Subject.objects.filter(owner=self.user, name="Economics").exists())

    def test_view_subjects_only_returns_current_users_subjects(self) -> None:
        own_subject = Subject.objects.create(owner=self.user, name="Biology")
        Subject.objects.create(owner=self.other_user, name="Private Math")

        response = self.client.get(reverse("subject-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subject_ids = {subject["id"] for subject in response.data}
        self.assertIn(own_subject.id, subject_ids)
        self.assertEqual(len(subject_ids), 1)

    def test_delete_subject_enforces_ownership(self) -> None:
        other_subject = Subject.objects.create(owner=self.other_user, name="Other Subject")

        response = self.client.delete(reverse("subject-detail", kwargs={"pk": other_subject.id}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Subject.objects.filter(id=other_subject.id).exists())


class ChapterExtractionTaskTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="task-student",
            email="task-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Task Notes",
            file=SimpleUploadedFile("task.pdf", b"fake pdf content", content_type="application/pdf"),
        )

    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_schedules_concept_extraction_for_each_chapter(self, mock_extract_text, mock_delay) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Basics
        - First concept

        Chapter 2: Advanced
        - Second concept
        """

        with self.captureOnCommitCallbacks(execute=True):
            extracted_count = extract_chapters_from_document(self.document.id)

        self.assertEqual(extracted_count, 2)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, "processing_concepts")
        self.assertEqual(list(self.document.chapters.values_list("sequence_number", flat=True)), [1, 2])
        self.assertEqual(mock_delay.call_count, 2)

    @patch("documents.tasks.download_object_to_tempfile")
    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_downloads_r2_file_without_local_file_path(
        self,
        mock_extract_text,
        mock_delay,
        mock_download,
    ) -> None:
        r2_document = Document.objects.create(
            owner=self.user,
            title="R2 Notes",
            storage_backend="r2",
            r2_object_key="documents/user-1/r2-notes.pdf",
            original_filename="r2-notes.pdf",
        )
        mock_download.return_value = "/tmp/r2-notes.pdf"
        mock_extract_text.return_value = """
        Chapter 1: R2 Basics
        - First concept
        """

        with self.captureOnCommitCallbacks(execute=True):
            extracted_count = extract_chapters_from_document(r2_document.id)

        r2_document.refresh_from_db()
        self.assertEqual(extracted_count, 1)
        self.assertEqual(r2_document.status, "processing_concepts")
        self.assertEqual(list(r2_document.chapters.values_list("title", flat=True)), ["Chapter 1: R2 Basics"])
        mock_download.assert_called_once_with("documents/user-1/r2-notes.pdf")
        mock_extract_text.assert_called_once_with("/tmp/r2-notes.pdf")
        self.assertEqual(mock_delay.call_count, 1)

    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_saves_parser_audit_metadata(self, mock_extract_text, mock_delay) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Basics
        - First concept

        Chapter 2: Advanced
        - Second concept
        """

        with self.captureOnCommitCallbacks(execute=True):
            extract_chapters_from_document(self.document.id)

        self.document.refresh_from_db()
        self.assertEqual(self.document.parser_version, "v1")
        self.assertEqual(self.document.parser_strategy, "one_line_chapter_heading")
        self.assertIsNotNone(self.document.parser_confidence_score)
        self.assertEqual(self.document.parser_warnings, [])
        self.assertEqual(self.document.parser_metadata["accepted_chapter_count"], 2)
        self.assertEqual(
            [chapter["sequence_number"] for chapter in self.document.parser_metadata["accepted_chapters"]],
            [1, 2],
        )
        self.assertEqual(self.document.parser_metadata["resolver_shadow"]["accepted_chapter_count"], 2)

    @override_settings(DOCUMENT_PARSER_USE_RESOLVER=False)
    @patch("documents.tasks.select_best_chapter_sequence")
    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_uses_legacy_parser_when_resolver_flag_is_off(
        self,
        mock_extract_text,
        mock_delay,
        mock_resolver,
    ) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Legacy Basics
        - First concept

        Chapter 2: Legacy Advanced
        - Second concept
        """
        mock_resolver.return_value = ChapterDetectionResult(
            accepted_chapters=[
                AcceptedChapter(
                    title="Chapter 1: Resolver Proposal",
                    sequence_number=1,
                    extracted_text="Resolver text",
                    confidence_score=0.99,
                    detection_methods=["resolver_test"],
                )
            ],
            rejected_candidates=[],
            strategy_used="shadow_best_sequence_resolver",
            confidence_score=0.99,
            warnings=[],
        )

        with self.captureOnCommitCallbacks(execute=True):
            extract_chapters_from_document(self.document.id)

        self.document.refresh_from_db()
        self.assertEqual(
            list(self.document.chapters.values_list("title", flat=True)),
            ["Chapter 1: Legacy Basics", "Chapter 2: Legacy Advanced"],
        )
        self.assertEqual(self.document.parser_strategy, "one_line_chapter_heading")
        self.assertEqual(self.document.parser_metadata["resolver_shadow"]["accepted_chapter_count"], 1)

    @override_settings(DOCUMENT_PARSER_USE_RESOLVER=True, DOCUMENT_PARSER_RESOLVER_CONFIDENCE_THRESHOLD=0.70)
    @patch("documents.tasks.select_best_chapter_sequence")
    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_uses_high_confidence_resolver_when_flag_is_on(
        self,
        mock_extract_text,
        mock_delay,
        mock_resolver,
    ) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Legacy Basics
        Legacy text.
        """
        mock_resolver.return_value = ChapterDetectionResult(
            accepted_chapters=[
                AcceptedChapter(
                    title="Chapter 1: Resolver Basics",
                    sequence_number=1,
                    extracted_text="Resolver selected text.",
                    confidence_score=0.95,
                    detection_methods=["resolver_test"],
                )
            ],
            rejected_candidates=[],
            strategy_used="shadow_best_sequence_resolver",
            confidence_score=0.95,
            warnings=[],
        )

        with self.captureOnCommitCallbacks(execute=True):
            extracted_count = extract_chapters_from_document(self.document.id)

        self.document.refresh_from_db()
        self.assertEqual(extracted_count, 1)
        self.assertEqual(list(self.document.chapters.values_list("title", flat=True)), ["Chapter 1: Resolver Basics"])
        self.assertEqual(self.document.parser_strategy, "resolver")
        self.assertEqual(self.document.parser_confidence_score, 0.95)

    @override_settings(DOCUMENT_PARSER_USE_RESOLVER=True, DOCUMENT_PARSER_RESOLVER_CONFIDENCE_THRESHOLD=0.70)
    @patch("documents.tasks.select_best_chapter_sequence")
    @patch("documents.tasks.extract_concepts_from_chapter.delay")
    @patch("documents.tasks.extract_text_from_pdf")
    def test_chapter_extraction_falls_back_to_legacy_when_resolver_confidence_is_low(
        self,
        mock_extract_text,
        mock_delay,
        mock_resolver,
    ) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Legacy Basics
        Legacy text.
        """
        mock_resolver.return_value = ChapterDetectionResult(
            accepted_chapters=[
                AcceptedChapter(
                    title="Chapter 1: Low Confidence Resolver",
                    sequence_number=1,
                    extracted_text="Weak resolver text.",
                    confidence_score=0.40,
                    detection_methods=["resolver_test"],
                )
            ],
            rejected_candidates=[],
            strategy_used="shadow_best_sequence_resolver",
            confidence_score=0.40,
            warnings=["Resolver was uncertain."],
        )

        with self.captureOnCommitCallbacks(execute=True):
            extract_chapters_from_document(self.document.id)

        self.document.refresh_from_db()
        self.assertEqual(list(self.document.chapters.values_list("title", flat=True)), ["Chapter 1: Legacy Basics"])
        self.assertEqual(self.document.parser_strategy, "legacy_fallback")
        self.assertTrue(any("did not meet the confidence threshold" in warning for warning in self.document.parser_warnings))


class ParserDryRunCommandTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="parser-command-student",
            email="parser-command-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Parser Command Notes",
            file=SimpleUploadedFile("parser-command.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        Chapter.objects.create(document=self.document, title="Existing Chapter", sequence_number=1)

    @patch("documents.management.commands.parser_dry_run.extract_text_from_pdf")
    def test_parser_dry_run_prints_metadata_without_modifying_database(self, mock_extract_text) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Basics
        First body.

        Chapter 2: Advanced
        Second body.
        """
        output = StringIO()

        call_command("parser_dry_run", self.document.id, stdout=output)

        self.assertIn("Document: Parser Command Notes", output.getvalue())
        self.assertIn("Parser strategy: one_line_chapter_heading", output.getvalue())
        self.assertIn("Accepted chapter count: 2", output.getvalue())
        self.assertIn("1. Chapter 1: Basics", output.getvalue())
        self.assertIn("Dry run complete. No database changes were made.", output.getvalue())
        self.assertEqual(list(self.document.chapters.values_list("title", flat=True)), ["Existing Chapter"])

    def test_parser_dry_run_handles_missing_document_gracefully(self) -> None:
        with self.assertRaisesMessage(CommandError, "Document 999999 does not exist."):
            call_command("parser_dry_run", 999999, stdout=StringIO())


class ParserPreviewCommandTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="parser-preview-student",
            email="parser-preview-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Parser Preview Notes",
            file=SimpleUploadedFile("parser-preview.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        Chapter.objects.create(document=self.document, title="Stored Chapter", sequence_number=1)

    @patch("documents.management.commands.parser_preview.extract_text_from_pdf")
    def test_parser_preview_shows_stored_and_proposed_chapters_without_modifying_database(self, mock_extract_text) -> None:
        mock_extract_text.return_value = """
        Chapter 1: Basics
        First body.

        Chapter 2: Advanced
        Second body.
        """
        output = StringIO()

        call_command("parser_preview", self.document.id, stdout=output)

        self.assertIn("Current stored chapters:", output.getvalue())
        self.assertIn("1. Stored Chapter", output.getvalue())
        self.assertIn("Legacy parser proposal (2 chapters):", output.getvalue())
        self.assertIn("Resolver proposal (2 chapters):", output.getvalue())
        self.assertIn("Preview complete. No database changes were made.", output.getvalue())
        self.assertEqual(list(self.document.chapters.values_list("title", flat=True)), ["Stored Chapter"])

    def test_parser_preview_handles_missing_document_gracefully(self) -> None:
        with self.assertRaisesMessage(CommandError, "Document 999999 does not exist."):
            call_command("parser_preview", 999999, stdout=StringIO())


class ParserReprocessCommandTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="parser-reprocess-student",
            email="parser-reprocess-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Parser Reprocess Notes",
            file=SimpleUploadedFile("parser-reprocess.pdf", b"fake pdf content", content_type="application/pdf"),
        )

    def test_parser_reprocess_requires_confirm_flag(self) -> None:
        with self.assertRaisesMessage(CommandError, "Refusing to reprocess without --confirm"):
            call_command("parser_reprocess", self.document.id, stdout=StringIO())

    @patch("documents.management.commands.parser_reprocess.extract_chapters_from_document")
    def test_parser_reprocess_runs_when_confirmed_and_no_progress_exists(self, mock_extract_chapters) -> None:
        mock_extract_chapters.return_value = 2
        output = StringIO()

        call_command("parser_reprocess", self.document.id, "--confirm", stdout=output)

        mock_extract_chapters.assert_called_once_with(self.document.id)
        self.assertIn("Reprocessed document", output.getvalue())

    @patch("documents.management.commands.parser_reprocess.extract_chapters_from_document")
    def test_parser_reprocess_blocks_when_progress_exists_without_force(self, mock_extract_chapters) -> None:
        chapter = Chapter.objects.create(document=self.document, title="Chapter", sequence_number=1)
        concept = Concept.objects.create(chapter=chapter, title="Concept", sequence_number=1)
        ChapterProgress.objects.create(user=self.user, chapter=chapter)
        ConceptProgress.objects.create(user=self.user, concept=concept)

        with self.assertRaisesMessage(CommandError, "Learning progress exists for this document"):
            call_command("parser_reprocess", self.document.id, "--confirm", stdout=StringIO())

        mock_extract_chapters.assert_not_called()

    @patch("documents.management.commands.parser_reprocess.extract_chapters_from_document")
    def test_parser_reprocess_allows_progress_reset_when_force_flag_is_present(self, mock_extract_chapters) -> None:
        mock_extract_chapters.return_value = 1
        chapter = Chapter.objects.create(document=self.document, title="Chapter", sequence_number=1)
        concept = Concept.objects.create(chapter=chapter, title="Concept", sequence_number=1)
        ConceptProgress.objects.create(user=self.user, concept=concept)
        output = StringIO()

        call_command("parser_reprocess", self.document.id, "--confirm", "--force-reset-progress", stdout=output)

        mock_extract_chapters.assert_called_once_with(self.document.id)
        self.assertIn("Force reset enabled", output.getvalue())

    def test_parser_reprocess_handles_missing_document_gracefully(self) -> None:
        with self.assertRaisesMessage(CommandError, "Document 999999 does not exist."):
            call_command("parser_reprocess", 999999, "--confirm", stdout=StringIO())


class ChapterConceptApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-student",
            email="api-student@example.com",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-student",
            email="other-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            owner=self.user,
            title="Math Notes",
            file=SimpleUploadedFile("math.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Algebra", sequence_number=1)

    def test_lists_concepts_for_user_owned_chapter_in_sequence_order(self) -> None:
        Concept.objects.create(chapter=self.chapter, title="Variables", sequence_number=2)
        Concept.objects.create(chapter=self.chapter, title="Expressions", sequence_number=1)

        response = self.client.get(reverse("chapter-concept-list", kwargs={"chapter_id": self.chapter.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["title"] for item in response.data], ["Expressions", "Variables"])

    def test_subject_filter_keeps_concepts_inside_selected_subject_context(self) -> None:
        math = Subject.objects.create(owner=self.user, name="Math")
        literature = Subject.objects.create(owner=self.user, name="Literature")
        self.document.subject = math
        self.document.save(update_fields=["subject"])
        Concept.objects.create(chapter=self.chapter, title="Variables", sequence_number=1)

        matching_response = self.client.get(
            reverse("chapter-concept-list", kwargs={"chapter_id": self.chapter.id}),
            {"subject": math.id},
        )
        mismatched_response = self.client.get(
            reverse("chapter-concept-list", kwargs={"chapter_id": self.chapter.id}),
            {"subject": literature.id},
        )

        self.assertEqual(matching_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["title"] for item in matching_response.data], ["Variables"])
        self.assertEqual(mismatched_response.status_code, status.HTTP_200_OK)
        self.assertEqual(mismatched_response.data, [])

    def test_does_not_list_concepts_for_another_users_chapter(self) -> None:
        other_document = Document.objects.create(
            owner=self.other_user,
            title="Private Notes",
            file=SimpleUploadedFile("private.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        other_chapter = Chapter.objects.create(document=other_document, title="Private", sequence_number=1)
        Concept.objects.create(chapter=other_chapter, title="Hidden", sequence_number=1)

        response = self.client.get(reverse("chapter-concept-list", kwargs={"chapter_id": other_chapter.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
