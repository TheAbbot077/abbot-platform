from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from documents.models import Chapter, Concept, Document, Subject

from .grading import submit_current_concept_answers
from .dashboard import build_progress_dashboard
from .forgetting import calculate_decayed_mastery
from .mcq import (
    FIRST_ATTEMPT,
    REINFORCEMENT_ATTEMPT,
    _bloom_distribution_for_attempt,
    _question_matches_current_concept,
    get_or_generate_current_concept_mcqs,
)
from .models import (
    BloomLevel,
    ChapterProgress,
    ConceptLesson,
    ConceptMastery,
    ConceptProgress,
    MasteryStrength,
    ProgressStatus,
    QuizAttempt,
    QuizQuestion,
    QuizQuestionType,
    RecommendationPriority,
    ReinforcementRecommendation,
    StudentAIReinforcementReport,
    StudentAIMemory,
    StudentAISpotQuizAttempt,
    TutorMessage,
)
from .openai_client import OpenAIServiceError
from .prompts import (
    MCQ_INSTRUCTIONS,
    TUTOR_ANSWER_INSTRUCTIONS,
    TUTOR_ANSWER_RESPONSE_SCHEMA,
    TUTOR_INSTRUCTIONS,
    TUTOR_RESPONSE_SCHEMA,
    build_mcq_input,
    build_student_ai_answer_input,
    build_tutor_answer_input,
    build_tutor_input,
)
from .restart import restart_chapter, restart_concept, restart_document
from .serializers import QuizAttemptResultSerializer
from .services import get_current_unlocked_concept, get_document_progress, mark_concept_mastered
from .spot_quiz import due_student_ai_memories, process_student_ai_spot_quiz, run_due_student_ai_spot_quizzes
from .student_ai import answer_student_ai_question, calculate_student_ai_retention, teach_student_ai_memory
from .tutor import _literary_metadata_for_concept, _normalize_lesson, answer_current_concept_question, teach_current_unlocked_concept


class ProgressModelTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="student",
            email="student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Chemistry Notes",
            file=SimpleUploadedFile("chemistry.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Atoms", sequence_number=1)
        self.concept = Concept.objects.create(chapter=self.chapter, title="Atomic Number", sequence_number=1)

    def test_chapter_progress_is_unique_per_user_and_chapter(self) -> None:
        ChapterProgress.objects.create(
            user=self.user,
            chapter=self.chapter,
            status=ProgressStatus.UNLOCKED,
        )

        with self.assertRaises(IntegrityError):
            ChapterProgress.objects.create(
                user=self.user,
                chapter=self.chapter,
                status=ProgressStatus.IN_PROGRESS,
            )

    def test_concept_progress_is_unique_per_user_and_concept(self) -> None:
        ConceptProgress.objects.create(
            user=self.user,
            concept=self.concept,
            status=ProgressStatus.UNLOCKED,
        )

        with self.assertRaises(IntegrityError):
            ConceptProgress.objects.create(
                user=self.user,
                concept=self.concept,
                status=ProgressStatus.IN_PROGRESS,
            )


class SequentialUnlockingServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="unlock-student",
            email="unlock-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Ordered Course",
            file=SimpleUploadedFile("course.pdf", b"fake pdf content", content_type="application/pdf"),
        )

        self.chapter_2 = Chapter.objects.create(document=self.document, title="Second", sequence_number=2)
        self.chapter_1 = Chapter.objects.create(document=self.document, title="First", sequence_number=1)

        self.chapter_1_concept_2 = Concept.objects.create(
            chapter=self.chapter_1,
            title="First Chapter Concept 2",
            sequence_number=2,
        )
        self.chapter_1_concept_1 = Concept.objects.create(
            chapter=self.chapter_1,
            title="First Chapter Concept 1",
            sequence_number=1,
        )
        self.chapter_2_concept_1 = Concept.objects.create(
            chapter=self.chapter_2,
            title="Second Chapter Concept 1",
            sequence_number=1,
        )

    def test_first_concept_in_first_chapter_is_initially_available(self) -> None:
        current = get_current_unlocked_concept(self.user, self.document)

        self.assertEqual(current.concept, self.chapter_1_concept_1)
        self.assertEqual(current.progress.status, ProgressStatus.UNLOCKED)
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.chapter_1_concept_2).status,
            ProgressStatus.LOCKED,
        )
        self.assertEqual(
            ChapterProgress.objects.get(user=self.user, chapter=self.chapter_2).status,
            ProgressStatus.LOCKED,
        )

    def test_next_concept_unlocks_only_after_previous_concept_is_mastered(self) -> None:
        mark_concept_mastered(self.user, self.chapter_1_concept_1)

        current = get_current_unlocked_concept(self.user, self.document)

        self.assertEqual(current.concept, self.chapter_1_concept_2)
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.chapter_2_concept_1).status,
            ProgressStatus.LOCKED,
        )

    def test_next_chapter_unlocks_only_after_all_required_concepts_are_mastered(self) -> None:
        mark_concept_mastered(self.user, self.chapter_1_concept_1)
        mark_concept_mastered(self.user, self.chapter_1_concept_2)

        current = get_current_unlocked_concept(self.user, self.document)

        self.assertEqual(current.concept, self.chapter_2_concept_1)
        self.assertEqual(
            ChapterProgress.objects.get(user=self.user, chapter=self.chapter_1).status,
            ProgressStatus.MASTERED,
        )
        self.assertEqual(
            ChapterProgress.objects.get(user=self.user, chapter=self.chapter_2).status,
            ProgressStatus.UNLOCKED,
        )

    def test_document_progress_returns_chapters_in_sequence_order(self) -> None:
        progress_rows = get_document_progress(self.user, self.document)

        self.assertEqual([row.chapter for row in progress_rows], [self.chapter_1, self.chapter_2])


class SequentialUnlockingApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-unlock-student",
            email="api-unlock-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            owner=self.user,
            title="API Course",
            file=SimpleUploadedFile("api-course.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="First", sequence_number=1)
        self.concept_2 = Concept.objects.create(chapter=self.chapter, title="Second Concept", sequence_number=2)
        self.concept_1 = Concept.objects.create(chapter=self.chapter, title="First Concept", sequence_number=1)

    def test_current_concept_endpoint_returns_first_unlocked_concept(self) -> None:
        response = self.client.get(reverse("current-concept", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_concept"]["concept_id"], self.concept_1.id)
        self.assertEqual(response.data["current_concept"]["status"], ProgressStatus.UNLOCKED)

    def test_progress_endpoint_returns_chapter_and_concept_statuses(self) -> None:
        response = self.client.get(reverse("document-progress", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_id"], self.document.id)
        self.assertEqual(response.data["chapters"][0]["chapter_id"], self.chapter.id)
        self.assertEqual(
            [concept["concept_id"] for concept in response.data["chapters"][0]["concepts"]],
            [self.concept_1.id, self.concept_2.id],
        )
        self.assertEqual(response.data["chapters"][0]["concepts"][0]["status"], ProgressStatus.UNLOCKED)
        self.assertEqual(response.data["chapters"][0]["concepts"][1]["status"], ProgressStatus.LOCKED)


class RestartLearningServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="restart-student",
            email="restart-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Restart Course",
            file=SimpleUploadedFile("restart.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter_1 = Chapter.objects.create(document=self.document, title="First", sequence_number=1)
        self.chapter_2 = Chapter.objects.create(document=self.document, title="Second", sequence_number=2)
        self.concept_1 = Concept.objects.create(chapter=self.chapter_1, title="Alpha", sequence_number=1)
        self.concept_2 = Concept.objects.create(chapter=self.chapter_1, title="Beta", sequence_number=2)
        self.concept_3 = Concept.objects.create(chapter=self.chapter_2, title="Gamma", sequence_number=1)

    def _add_learning_records(self, concept: Concept) -> None:
        ConceptLesson.objects.create(
            user=self.user,
            concept=concept,
            source_excerpt="source",
            explanation="lesson",
            examples=["example"],
            next_action="ready_for_mcq",
        )
        TutorMessage.objects.create(
            user=self.user,
            concept=concept,
            student_question="question",
            tutor_answer="answer",
            source_mode="document_only",
        )
        QuizQuestion.objects.create(
            concept=concept,
            question_text="Question?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            explanation="Because A.",
        )
        QuizAttempt.objects.create(
            user=self.user,
            concept=concept,
            submitted_answers={},
            total_questions=1,
            correct_answers=1,
            score=100,
            passed=True,
        )
        ConceptMastery.objects.create(user=self.user, concept=concept, mastery_score=100)

    def test_restart_concept_clears_attempts_and_makes_it_available_without_reordering(self) -> None:
        mark_concept_mastered(self.user, self.concept_1)
        self._add_learning_records(self.concept_1)

        restart_concept(self.user, self.concept_1)

        progress = ConceptProgress.objects.get(user=self.user, concept=self.concept_1)
        self.assertEqual(progress.status, ProgressStatus.UNLOCKED)
        self.assertEqual(progress.attempts_count, 0)
        self.assertIsNone(progress.last_score)
        self.assertFalse(QuizAttempt.objects.filter(user=self.user, concept=self.concept_1).exists())
        self.assertFalse(ConceptLesson.objects.filter(user=self.user, concept=self.concept_1).exists())
        self.assertFalse(QuizQuestion.objects.filter(concept=self.concept_1).exists())
        self.assertEqual([concept.sequence_number for concept in self.chapter_1.concepts.order_by("sequence_number")], [1, 2])

    def test_restart_chapter_resets_chapter_and_locks_later_chapters(self) -> None:
        mark_concept_mastered(self.user, self.concept_1)
        mark_concept_mastered(self.user, self.concept_2)
        mark_concept_mastered(self.user, self.concept_3)

        restart_chapter(self.user, self.chapter_1)

        self.assertEqual(ConceptProgress.objects.get(user=self.user, concept=self.concept_1).status, ProgressStatus.UNLOCKED)
        self.assertEqual(ConceptProgress.objects.get(user=self.user, concept=self.concept_2).status, ProgressStatus.LOCKED)
        self.assertEqual(ConceptProgress.objects.get(user=self.user, concept=self.concept_3).status, ProgressStatus.LOCKED)
        self.assertEqual(ChapterProgress.objects.get(user=self.user, chapter=self.chapter_1).status, ProgressStatus.UNLOCKED)
        self.assertEqual(ChapterProgress.objects.get(user=self.user, chapter=self.chapter_2).status, ProgressStatus.LOCKED)

    def test_restart_document_resets_all_progress_but_keeps_file_and_order(self) -> None:
        mark_concept_mastered(self.user, self.concept_1)
        mark_concept_mastered(self.user, self.concept_2)
        self._add_learning_records(self.concept_1)

        restart_document(self.user, self.document)

        self.document.refresh_from_db()
        self.assertTrue(self.document.file.name)
        self.assertEqual(get_current_unlocked_concept(self.user, self.document).concept, self.concept_1)
        self.assertFalse(QuizAttempt.objects.filter(user=self.user, concept__chapter__document=self.document).exists())
        self.assertEqual([chapter.sequence_number for chapter in self.document.chapters.order_by("sequence_number")], [1, 2])


class TutorServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="tutor-student",
            email="tutor-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Tutor Course",
            file=SimpleUploadedFile("tutor.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Fractions",
            sequence_number=1,
            extracted_text="Fractions show parts of a whole. Equivalent fractions have the same value.",
        )
        self.concept_1 = Concept.objects.create(
            chapter=self.chapter,
            title="Fractions",
            sequence_number=1,
            summary="Fractions show parts of a whole.",
        )
        self.concept_2 = Concept.objects.create(
            chapter=self.chapter,
            title="Equivalent Fractions",
            sequence_number=2,
            summary="Equivalent fractions have the same value.",
        )

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_tutor_teaches_only_current_unlocked_concept(self, mock_generate) -> None:
        QuizQuestion.objects.create(
            concept=self.concept_1,
            question_text="Old broad chapter question?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            explanation="Old explanation.",
        )
        mock_generate.return_value = {
            "concept_id": self.concept_1.id,
            "concept_name": self.concept_1.title,
            "explanation": "A fraction is a way to show part of a whole.",
            "examples": ["1/2 means one out of two equal parts."],
            "next_action": "ready_for_mcq",
        }

        lesson = teach_current_unlocked_concept(self.user, self.document)

        self.assertEqual(lesson["concept_id"], self.concept_1.id)
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs["concept_name"], "Fractions")
        self.assertIn("parts of a whole", mock_generate.call_args.kwargs["source_excerpt"])
        stored_lesson = ConceptLesson.objects.get(user=self.user, concept=self.concept_1)
        self.assertEqual(stored_lesson.explanation, "A fraction is a way to show part of a whole.")
        self.assertEqual(stored_lesson.visual_content, {})
        self.assertFalse(QuizQuestion.objects.filter(concept=self.concept_1, is_answered=False).exists())
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.concept_1).status,
            ProgressStatus.IN_PROGRESS,
        )
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.concept_2).status,
            ProgressStatus.LOCKED,
        )

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_tutor_returns_none_when_every_required_concept_is_mastered(self, mock_generate) -> None:
        mark_concept_mastered(self.user, self.concept_1)
        mark_concept_mastered(self.user, self.concept_2)

        lesson = teach_current_unlocked_concept(self.user, self.document)

        self.assertIsNone(lesson)
        mock_generate.assert_not_called()

    def test_tutor_normalizes_extra_examples_before_serialization(self) -> None:
        lesson = _normalize_lesson(
            {
                "concept_id": self.concept_1.id,
                "concept_name": self.concept_1.title,
                "explanation": "Fractions show parts of a whole.",
                "examples": ["one", "two", "three", "four"],
                "next_action": "ready_for_mcq",
            }
        )

        self.assertEqual(lesson["examples"], ["one", "two", "three"])

    def test_tutor_normalizes_common_lesson_response_variants(self) -> None:
        lesson = _normalize_lesson(
            {
                "lesson": {
                    "lesson_text": "Fractions show equal parts of a whole.",
                    "examples": "A half is one of two equal parts.",
                    "next_action": "take_quiz",
                }
            }
        )

        self.assertEqual(lesson["explanation"], "Fractions show equal parts of a whole.")
        self.assertEqual(lesson["examples"], ["A half is one of two equal parts."])
        self.assertEqual(lesson["next_action"], "ready_for_mcq")
        self.assertIsNone(lesson["visual_content"])

    def test_tutor_accepts_structured_visual_intent(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A parabola curves upward for this equation.",
                "examples": ["The graph of y = x^2 is U-shaped."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "graph",
                    "title": "Graph of y = x^2",
                    "description": "A parabola opening upward on a coordinate plane.",
                    "expression": "y = x^2",
                    "render_mode": "function_plot",
                },
            }
        )

        self.assertEqual(lesson["visual_content"]["type"], "graph")
        self.assertEqual(lesson["visual_content"]["render_mode"], "function_plot")

    def test_tutor_keeps_non_visual_concepts_without_forcing_visual_content(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A definition can be explained clearly with words.",
                "examples": ["A key term can have a short example."],
                "next_action": "ready_for_mcq",
                "visual_content": None,
            }
        )

        self.assertEqual(lesson["explanation"], "A definition can be explained clearly with words.")
        self.assertIsNone(lesson["visual_content"])

    def test_tutor_accepts_structured_geometry_visual_intent(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A right triangle has one angle that measures 90 degrees.",
                "examples": ["Triangle ABC can have a right angle at C."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "geometry",
                    "title": "Right triangle ABC",
                    "description": "A triangle with a right angle marked at C.",
                    "expression": "",
                    "render_mode": "geometry_diagram",
                    "shape": "triangle",
                    "labels": ["A", "B", "C"],
                    "annotations": [{"label": "90°", "position": "corner_C"}],
                },
            }
        )

        self.assertEqual(lesson["visual_content"]["type"], "geometry")
        self.assertEqual(lesson["visual_content"]["shape"], "triangle")
        self.assertEqual(lesson["visual_content"]["labels"], ["A", "B", "C"])
        self.assertEqual(lesson["visual_content"]["annotations"][0]["label"], "90°")

    def test_tutor_accepts_structured_chart_visual_intent(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A bar chart can compare values across categories.",
                "examples": ["Study time can be compared by day."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "chart",
                    "title": "Study time by day",
                    "description": "A bar chart comparing hours of study.",
                    "expression": "",
                    "render_mode": "statistics_chart",
                    "chart_type": "bar",
                    "x_label": "Day",
                    "y_label": "Hours",
                    "data": [{"label": "Mon", "value": 2}, {"label": "Tue", "value": 3}],
                },
            }
        )

        self.assertEqual(lesson["visual_content"]["type"], "chart")
        self.assertEqual(lesson["visual_content"]["chart_type"], "bar")
        self.assertEqual(lesson["visual_content"]["data"][0]["label"], "Mon")
        self.assertEqual(lesson["visual_content"]["data"][1]["value"], 3.0)

    def test_tutor_accepts_supply_and_demand_line_graph_visual_intent(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A demand curve can be shown as a simple downward-sloping line.",
                "examples": ["As price rises, quantity demanded often falls."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "graph",
                    "title": "Simple demand curve",
                    "description": "A line graph showing demand decreasing as x increases.",
                    "expression": "y = -x + 10",
                    "render_mode": "function_plot",
                },
            }
        )

        self.assertEqual(lesson["visual_content"]["type"], "graph")
        self.assertEqual(lesson["visual_content"]["expression"], "y = -x + 10")

    def test_tutor_strips_unsafe_visual_content_without_dropping_explanation(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "This lesson is still useful without the unsafe visual.",
                "examples": ["The explanation should remain."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "graph",
                    "title": "Unsafe graph",
                    "description": "<svg><script>alert(1)</script></svg>",
                    "expression": "y = x^2",
                    "render_mode": "function_plot",
                },
            }
        )

        self.assertEqual(lesson["explanation"], "This lesson is still useful without the unsafe visual.")
        self.assertIsNone(lesson["visual_content"])

    def test_tutor_rejects_unsafe_or_unsupported_graph_expressions(self) -> None:
        invalid_visuals = [
            {"expression": "y = import(os)", "render_mode": "function_plot"},
            {"expression": "y = x.constructor", "render_mode": "function_plot"},
            {"expression": "z = x^2", "render_mode": "function_plot"},
            {"expression": "y = x^2", "render_mode": "conceptual_diagram"},
        ]

        for visual in invalid_visuals:
            lesson = _normalize_lesson(
                {
                    "explanation": "Graph validation should be strict.",
                    "examples": ["Only safe graph expressions are allowed."],
                    "next_action": "ready_for_mcq",
                    "visual_content": {
                        "type": "graph",
                        "title": "Graph",
                        "description": "Graph description",
                        **visual,
                    },
                }
            )
            self.assertIsNone(lesson["visual_content"])

    def test_tutor_accepts_table_visual_type(self) -> None:
        lesson = _normalize_lesson(
            {
                "explanation": "A table can compare categories.",
                "examples": ["Monday has 2 hours."],
                "next_action": "ready_for_mcq",
                "visual_content": {
                    "type": "table",
                    "title": "Study time table",
                    "description": "A simple table.",
                    "expression": "",
                    "render_mode": "statistics_chart",
                    "x_label": "Day",
                    "y_label": "Hours",
                    "data": [{"label": "Mon", "value": 2}],
                },
            }
        )

        self.assertEqual(lesson["visual_content"]["type"], "table")
        self.assertEqual(lesson["visual_content"]["chart_type"], "table")

    def test_tutor_prompt_schema_includes_optional_visual_content(self) -> None:
        visual_schema = TUTOR_RESPONSE_SCHEMA["schema"]["properties"]["visual_content"]

        self.assertIn("visual_content", TUTOR_RESPONSE_SCHEMA["schema"]["required"])
        self.assertIn("visual_content", TUTOR_ANSWER_RESPONSE_SCHEMA["schema"]["required"])
        self.assertIn("function_plot", visual_schema["anyOf"][0]["properties"]["render_mode"]["enum"])
        self.assertIn("chart", visual_schema["anyOf"][1]["properties"]["type"]["enum"])
        self.assertIn("table", visual_schema["anyOf"][1]["properties"]["type"]["enum"])
        self.assertIn("bar", visual_schema["anyOf"][1]["properties"]["chart_type"]["enum"])
        self.assertIn("geometry", visual_schema["anyOf"][2]["properties"]["type"]["enum"])
        self.assertIn("triangle", visual_schema["anyOf"][2]["properties"]["shape"]["enum"])
        self.assertIn("Do not invent unsupported visual types", TUTOR_INSTRUCTIONS)
        self.assertIn("Visual teaching intent", TUTOR_INSTRUCTIONS)
        self.assertIn("show me visually", TUTOR_ANSWER_INSTRUCTIONS)

    @patch("learning.tutor._answer_question_with_openai")
    def test_student_can_ask_question_about_current_concept_without_unlocking(self, mock_answer) -> None:
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept_1,
            source_excerpt="Fractions show parts of a whole.",
            explanation="A fraction shows part of a whole.",
            examples=["1/2 means one of two equal parts."],
            next_action="ready_for_mcq",
        )
        mock_answer.return_value = {
            "concept_id": self.concept_1.id,
            "student_question": "Why is the bottom number important?",
            "tutor_answer": "The bottom number tells how many equal parts make the whole.",
            "source_mode": "document_only",
            "next_action": "continue_studying",
        }

        answer = answer_current_concept_question(
            self.user,
            self.document,
            concept_id=self.concept_1.id,
            question="Why is the bottom number important?",
        )

        self.assertEqual(answer["concept_id"], self.concept_1.id)
        self.assertEqual(TutorMessage.objects.count(), 1)
        self.assertEqual(TutorMessage.objects.get().source_mode, "document_only")
        self.assertEqual(TutorMessage.objects.get().visual_content, {})
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.concept_1).status,
            ProgressStatus.UNLOCKED,
        )
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.concept_2).status,
            ProgressStatus.LOCKED,
        )

    @patch("learning.tutor._answer_question_with_openai")
    def test_student_cannot_ask_question_about_locked_future_concept(self, mock_answer) -> None:
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept_1,
            source_excerpt="Fractions show parts of a whole.",
            explanation="A fraction shows part of a whole.",
            examples=["1/2 means one of two equal parts."],
            next_action="ready_for_mcq",
        )

        with self.assertRaisesMessage(ValueError, "Questions can only be asked about the currently unlocked concept."):
            answer_current_concept_question(
                self.user,
                self.document,
                concept_id=self.concept_2.id,
                question="What are equivalent fractions?",
            )

        mock_answer.assert_not_called()

    @patch("learning.tutor._answer_question_with_openai")
    def test_general_knowledge_clarification_is_labeled_and_does_not_mark_passed(self, mock_answer) -> None:
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept_1,
            source_excerpt="Fractions show parts of a whole.",
            explanation="A fraction shows part of a whole.",
            examples=["1/2 means one of two equal parts."],
            next_action="ready_for_mcq",
        )
        mock_answer.return_value = {
            "concept_id": self.concept_1.id,
            "student_question": "Why are fractions useful in cooking?",
            "tutor_answer": "To clarify using general knowledge: recipes often use fractional amounts.",
            "source_mode": "general_knowledge_clarification",
            "next_action": "continue_studying",
        }

        answer_current_concept_question(
            self.user,
            self.document,
            concept_id=self.concept_1.id,
            question="Why are fractions useful in cooking?",
        )

        progress = ConceptProgress.objects.get(user=self.user, concept=self.concept_1)
        self.assertEqual(progress.status, ProgressStatus.UNLOCKED)
        self.assertIsNone(progress.mastered_at)
        self.assertEqual(TutorMessage.objects.get().source_mode, "general_knowledge_clarification")

    def test_tutor_answer_prompt_includes_chapter_objectives_and_source_modes(self) -> None:
        prompt = build_tutor_answer_input(
            concept_id=self.concept_1.id,
            concept_name=self.concept_1.title,
            concept_summary=self.concept_1.summary,
            source_excerpt="Fractions show parts of a whole.",
            chapter_objectives=["Understand fractions"],
            lesson_explanation="A fraction shows part of a whole.",
            lesson_examples=["1/2 means one of two equal parts."],
            student_question="Why is the bottom number important?",
        )

        self.assertIn("Understand fractions", prompt)
        self.assertIn("Concept-specific source excerpt", prompt)
        self.assertIn("Student question", prompt)

    def test_tutor_prompts_request_latex_for_math_only(self) -> None:
        lesson_prompt = build_tutor_input(
            concept_id=self.concept_1.id,
            concept_name="Exponents",
            concept_summary="Use powers to represent repeated multiplication.",
            source_excerpt="x squared can be written as x^2.",
        )
        answer_prompt = build_tutor_answer_input(
            concept_id=self.concept_1.id,
            concept_name="Exponents",
            concept_summary="Use powers to represent repeated multiplication.",
            source_excerpt="x squared can be written as x^2.",
            chapter_objectives=["Use exponents"],
            lesson_explanation="An exponent tells how many times to multiply a base.",
            lesson_examples=["2^3 means 2 multiplied by itself three times."],
            student_question="How should I write a square root?",
        )

        self.assertIn("Inline math must use \\( ... \\)", TUTOR_INSTRUCTIONS)
        self.assertIn("Block equations must use \\[ ... \\]", TUTOR_INSTRUCTIONS)
        self.assertIn("\\frac{a}{b}", TUTOR_INSTRUCTIONS)
        self.assertIn("\\sqrt{x}", TUTOR_ANSWER_INSTRUCTIONS)
        self.assertIn("do not wrap ordinary sentences in LaTeX", TUTOR_INSTRUCTIONS)
        self.assertIn("format only mathematical expressions in LaTeX", lesson_prompt)
        self.assertIn("format only mathematical expressions in LaTeX", answer_prompt)

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_literary_tutor_receives_chapter_metadata(self, mock_generate) -> None:
        self.chapter.title = "Chapter 1: The Visitor"
        self.chapter.extracted_text = "Mara waited at the gate. The lantern flickered in the rain."
        self.chapter.literary_metadata = {
            "section_title": "Chapter 1: The Visitor",
            "section_sequence": 1,
            "content_classification": "novel",
            "summary": "Mara waits at the gate during a storm.",
            "key_events": ["Mara waits at the gate."],
            "characters_present": ["Mara"],
            "themes": ["uncertainty"],
            "literary_devices": ["imagery"],
            "important_quotes": ["The lantern flickered in the rain."],
            "interpretation_questions": ["How does the setting build tension?"],
        }
        self.chapter.save(update_fields=["title", "extracted_text", "literary_metadata"])
        self.concept_1.title = "Chapter summary"
        self.concept_1.summary = "[Literary Toolkit] Explain what happens in this section."
        self.concept_1.save(update_fields=["title", "summary"])
        mock_generate.return_value = {
            "concept_id": self.concept_1.id,
            "concept_name": self.concept_1.title,
            "explanation": "This section introduces Mara waiting in a tense setting.",
            "examples": ["The flickering lantern creates uncertainty."],
            "next_action": "ready_for_mcq",
        }

        lesson = teach_current_unlocked_concept(self.user, self.document)

        self.assertEqual(mock_generate.call_args.kwargs["literary_metadata"]["content_classification"], "novel")
        self.assertIn("How does the setting build tension?", mock_generate.call_args.kwargs["literary_metadata"]["interpretation_questions"])
        self.assertTrue(lesson["is_literary"])
        self.assertEqual(lesson["literary_metadata"]["characters_present"], ["Mara"])
        stored_lesson = ConceptLesson.objects.get(user=self.user, concept=self.concept_1)
        self.assertEqual(stored_lesson.explanation, "This section introduces Mara waiting in a tense setting.")

    def test_literary_prompts_include_evidence_and_spoiler_guardrails(self) -> None:
        metadata = {
            "section_title": "Act 1, Scene 1",
            "summary": "Two characters argue at night.",
            "characters_present": ["Ari", "Bea"],
            "literary_devices": ["irony", "tone"],
            "interpretation_questions": ["What makes the scene tense?"],
        }
        lesson_prompt = build_tutor_input(
            concept_id=self.concept_1.id,
            concept_name="Conflict and tension",
            concept_summary="[Literary Toolkit] Identify the central struggle.",
            source_excerpt="Ari says, 'I am not afraid,' while stepping back.",
            literary_metadata=metadata,
        )
        answer_prompt = build_tutor_answer_input(
            concept_id=self.concept_1.id,
            concept_name="Conflict and tension",
            concept_summary="[Literary Toolkit] Identify the central struggle.",
            source_excerpt="Ari says, 'I am not afraid,' while stepping back.",
            chapter_objectives=["Analyze tension"],
            literary_metadata=metadata,
            lesson_explanation="The scene builds tension through words and action.",
            lesson_examples=["Ari's words contrast with stepping back."],
            student_question="Is this irony?",
        )

        self.assertIn("Literary section metadata", lesson_prompt)
        self.assertIn("Ari", lesson_prompt)
        self.assertIn("support an answer with evidence", lesson_prompt)
        self.assertIn("Avoid spoilers", lesson_prompt)
        self.assertIn("Do not invent events", answer_prompt)
        self.assertIn("Use general literary knowledge only to clarify terms", answer_prompt)

    def test_literary_metadata_helper_ignores_normal_concepts(self) -> None:
        self.chapter.literary_metadata = {"summary": "A stored literary summary."}
        self.chapter.save(update_fields=["literary_metadata"])

        self.assertEqual(_literary_metadata_for_concept(self.concept_1), {})

        self.concept_1.summary = "[Literary Toolkit] Explain the scene."
        self.concept_1.save(update_fields=["summary"])
        self.assertEqual(_literary_metadata_for_concept(self.concept_1), {"summary": "A stored literary summary."})


class TutorApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-tutor-student",
            email="api-tutor-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.subject = Subject.objects.create(owner=self.user, name="Biology")
        self.other_subject = Subject.objects.create(owner=self.user, name="Economics")
        self.document = Document.objects.create(
            owner=self.user,
            subject=self.subject,
            title="API Tutor Course",
            file=SimpleUploadedFile("api-tutor.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Photosynthesis",
            sequence_number=1,
            extracted_text="Photosynthesis lets plants make food using light.",
        )
        self.concept = Concept.objects.create(
            chapter=self.chapter,
            title="Photosynthesis",
            sequence_number=1,
            summary="Plants make food using light.",
        )

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_tutor_endpoint_returns_structured_lesson(self, mock_generate) -> None:
        mock_generate.return_value = {
            "concept_id": self.concept.id,
            "concept_name": "Photosynthesis",
            "explanation": "Photosynthesis is how plants use light to make food.",
            "examples": ["A leaf uses sunlight, water, and carbon dioxide."],
            "next_action": "ready_for_mcq",
        }

        response = self.client.post(reverse("tutor-current-concept", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["concept_id"], self.concept.id)
        self.assertEqual(response.data["concept_name"], "Photosynthesis")
        self.assertEqual(response.data["next_action"], "ready_for_mcq")

    def test_current_concept_response_includes_subject_context(self) -> None:
        response = self.client.get(
            reverse("current-concept", kwargs={"document_id": self.document.id}),
            {"subject": self.subject.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_concept"]["subject_id"], self.subject.id)
        self.assertEqual(response.data["current_concept"]["subject_name"], "Biology")

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_tutor_endpoint_rejects_mismatched_subject_context(self, mock_generate) -> None:
        response = self.client.post(
            f"{reverse('tutor-current-concept', kwargs={'document_id': self.document.id})}?subject={self.other_subject.id}",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_generate.assert_not_called()

    @patch("learning.tutor._generate_lesson_with_openai")
    def test_tutor_endpoint_returns_clean_error_when_openai_rejects_request(self, mock_generate) -> None:
        mock_generate.side_effect = OpenAIServiceError("OpenAI rejected the configured API key.", status_code=401)

        response = self.client.post(reverse("tutor-current-concept", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["detail"], "OpenAI rejected the configured API key.")

    @patch("learning.tutor._answer_question_with_openai")
    def test_tutor_ask_endpoint_returns_structured_answer(self, mock_answer) -> None:
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept,
            source_excerpt="Photosynthesis lets plants make food using light.",
            explanation="Photosynthesis is how plants use light to make food.",
            examples=["A leaf uses sunlight."],
            next_action="ready_for_mcq",
        )
        mock_answer.return_value = {
            "concept_id": self.concept.id,
            "student_question": "Why do plants need light?",
            "tutor_answer": "Light provides the energy plants use during photosynthesis.",
            "source_mode": "document_plus_general_knowledge",
            "next_action": "continue_studying",
        }

        response = self.client.post(
            reverse("tutor-ask"),
            {"concept_id": self.concept.id, "question": "Why do plants need light?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["concept_id"], self.concept.id)
        self.assertEqual(response.data["student_question"], "Why do plants need light?")
        self.assertEqual(response.data["source_mode"], "document_plus_general_knowledge")

    @patch("learning.tutor._answer_question_with_openai")
    def test_tutor_ask_rejects_mismatched_subject_context(self, mock_answer) -> None:
        response = self.client.post(
            reverse("tutor-ask"),
            {
                "concept_id": self.concept.id,
                "subject_id": self.other_subject.id,
                "question": "Why do plants need light?",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_answer.assert_not_called()


class MCQGenerationServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="mcq-student",
            email="mcq-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="MCQ Course",
            file=SimpleUploadedFile("mcq.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Decimals",
            sequence_number=1,
            extracted_text="Decimals are numbers that use place value after a decimal point.",
        )
        self.current_concept = Concept.objects.create(
            chapter=self.chapter,
            title="Decimals",
            sequence_number=1,
            summary="Decimals use place value after a decimal point.",
        )
        self.locked_concept = Concept.objects.create(
            chapter=self.chapter,
            title="Rounding Decimals",
            sequence_number=2,
            summary="Rounding decimals changes them to a nearby simpler value.",
        )
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.current_concept,
            source_excerpt="Decimals are numbers that use place value after a decimal point.",
            explanation="Decimals use place value after a decimal point.",
            examples=["0.5 is five tenths."],
            next_action="ready_for_mcq",
        )

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_generates_and_stores_mcqs_for_current_unlocked_concept(self, mock_generate) -> None:
        mock_generate.return_value = [
            {
                "question_text": "What does a decimal point help show?",
                "options": {
                    "A": "Place value after ones",
                    "B": "Only whole numbers",
                    "C": "Roman numerals",
                    "D": "Chapter order",
                },
                "correct_option": "A",
                "explanation": "The decimal point separates whole-number places from fractional places.",
                "bloom_level": "understand",
            }
        ]

        questions = get_or_generate_current_concept_mcqs(self.user, self.document, question_count=1)

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].concept, self.current_concept)
        self.assertEqual(questions[0].bloom_level, BloomLevel.UNDERSTAND)
        self.assertEqual(questions[0].correct_option, "A")
        self.assertFalse(questions[0].is_answered)
        self.assertEqual(QuizQuestion.objects.filter(concept=self.locked_concept).count(), 0)
        self.assertIn("tutor_explanation", mock_generate.call_args.kwargs)
        self.assertNotIn("source_chapter_text", mock_generate.call_args.kwargs)
        self.assertEqual(mock_generate.call_args.kwargs["attempt_mode"], FIRST_ATTEMPT)
        self.assertEqual(mock_generate.call_args.kwargs["bloom_distribution"], {"remember": 1})

    def test_rejects_generated_question_that_mentions_future_locked_concept(self) -> None:
        question = {
            "question_text": "How do rounding decimals work?",
            "options": {"A": "Round up", "B": "Place value", "C": "Ignore decimals", "D": "None"},
            "correct_option": "A",
            "explanation": "Rounding decimals changes them to a nearby simpler value.",
        }

        is_allowed = _question_matches_current_concept(
            question,
            concept_name="Decimals",
            tutor_explanation="Decimals use place value after a decimal point.",
            tutor_examples=["0.5 is five tenths."],
            locked_concept_titles=["Rounding Decimals"],
        )

        self.assertFalse(is_allowed)

    def test_requires_tutor_lesson_before_generating_mcqs(self) -> None:
        ConceptLesson.objects.filter(user=self.user, concept=self.current_concept).delete()

        with self.assertRaisesMessage(ValueError, "Teach the current concept before generating practice questions."):
            get_or_generate_current_concept_mcqs(self.user, self.document)

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_mcqs_ignore_clarification_messages(self, mock_generate) -> None:
        TutorMessage.objects.create(
            user=self.user,
            concept=self.current_concept,
            student_question="Why do people use decimals in baseball stats?",
            tutor_answer="To clarify using general knowledge: batting averages use decimals.",
            source_mode="general_knowledge_clarification",
        )
        mock_generate.return_value = [
            {
                "question_text": "What does a decimal point help show?",
                "options": {
                    "A": "Place value after ones",
                    "B": "Only baseball averages",
                    "C": "Roman numerals",
                    "D": "Chapter order",
                },
                "correct_option": "A",
                "explanation": "The decimal point separates whole-number places from fractional places.",
            }
        ]

        get_or_generate_current_concept_mcqs(self.user, self.document, question_count=1)

        kwargs = mock_generate.call_args.kwargs
        self.assertIn("tutor_explanation", kwargs)
        self.assertNotIn("clarification", kwargs)
        self.assertNotIn("tutor_messages", kwargs)

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_visual_content_does_not_affect_mcq_generation_or_unlocking(self, mock_generate) -> None:
        ConceptLesson.objects.filter(user=self.user, concept=self.current_concept).update(
            visual_content={
                "type": "graph",
                "title": "Graph of y = x^2",
                "description": "A parabola.",
                "expression": "y = x^2",
                "render_mode": "function_plot",
            }
        )
        mock_generate.return_value = [
            {
                "question_text": "What does a decimal point help show?",
                "options": {
                    "A": "Place value after ones",
                    "B": "Only the shape of a graph",
                    "C": "Roman numerals",
                    "D": "Chapter order",
                },
                "correct_option": "A",
                "explanation": "The decimal point separates whole-number places from fractional places.",
                "bloom_level": "understand",
            }
        ]

        get_or_generate_current_concept_mcqs(self.user, self.document, question_count=1)

        kwargs = mock_generate.call_args.kwargs
        self.assertNotIn("visual_content", kwargs)
        self.assertNotIn("render_mode", kwargs)
        self.assertEqual(ConceptProgress.objects.get(user=self.user, concept=self.current_concept).status, ProgressStatus.UNLOCKED)
        self.assertEqual(ConceptProgress.objects.get(user=self.user, concept=self.locked_concept).status, ProgressStatus.LOCKED)

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_reinforcement_mcqs_use_stronger_bloom_distribution(self, mock_generate) -> None:
        QuizAttempt.objects.create(
            user=self.user,
            concept=self.current_concept,
            submitted_answers={},
            total_questions=1,
            correct_answers=0,
            score=0,
            passed=False,
        )
        mock_generate.return_value = [
            {
                "question_text": "Which example best uses decimal place value?",
                "options": {
                    "A": "0.5 means five tenths",
                    "B": "0.5 means five hundreds",
                    "C": "0.5 is a whole number",
                    "D": "0.5 is a chapter title",
                },
                "correct_option": "A",
                "explanation": "The digit 5 is in the tenths place.",
                "bloom_level": "apply",
            }
        ]

        get_or_generate_current_concept_mcqs(self.user, self.document, question_count=5)

        kwargs = mock_generate.call_args.kwargs
        self.assertEqual(kwargs["attempt_mode"], REINFORCEMENT_ATTEMPT)
        self.assertEqual(kwargs["bloom_distribution"], {"remember": 1, "understand": 1, "apply": 1, "analyze": 1, "evaluate": 1})

    def test_mcq_prompt_excludes_clarification_chat_and_general_knowledge(self) -> None:
        prompt = build_mcq_input(
            concept_id=self.current_concept.id,
            concept_name=self.current_concept.title,
            concept_summary=self.current_concept.summary,
            source_excerpt="Decimals are numbers that use place value after a decimal point.",
            tutor_explanation="Decimals use place value after a decimal point.",
            tutor_examples=["0.5 is five tenths."],
            question_count=3,
            attempt_mode=FIRST_ATTEMPT,
            bloom_distribution={"remember": 1, "understand": 1, "apply": 1},
        )

        self.assertIn("Do not generate questions from clarification chat or general knowledge add-ons", prompt)
        self.assertIn("Only test the official concept lesson", prompt)
        self.assertIn("Bloom level target distribution", prompt)
        self.assertIn("Do not use create-level assessment yet", prompt)

    def test_literary_prompt_requests_interpretive_checks_without_spoilers(self) -> None:
        prompt = build_mcq_input(
            concept_id=self.current_concept.id,
            concept_name="Interpretation questions",
            concept_summary="[Literary Toolkit] Practice explaining what the text means.",
            source_excerpt="Mara says, 'The gate is open,' while refusing to step forward.",
            tutor_explanation="The moment suggests hesitation and tension.",
            tutor_examples=["The open gate can symbolize a choice."],
            question_count=3,
            attempt_mode=FIRST_ATTEMPT,
            bloom_distribution={"understand": 1, "apply": 1, "analyze": 1},
        )

        self.assertIn("short_answer for quote interpretation", prompt)
        self.assertIn("more than one answer may be reasonable", MCQ_INSTRUCTIONS)
        self.assertIn("For literature, do not ask about later", MCQ_INSTRUCTIONS)
        self.assertIn("Do not introduce spoilers", prompt)

    def test_literary_short_answer_question_is_allowed_for_current_section(self) -> None:
        question = {
            "question_type": "short_answer",
            "question_text": "How does the open gate help create tension?",
            "options": {"A": "", "B": "", "C": "", "D": ""},
            "correct_option": "",
            "explanation": "A strong answer connects the open gate to hesitation and choice.",
            "expected_answer": "The gate can suggest a choice, while Mara's hesitation creates tension.",
            "evidence_guidance": "Use the phrase about the open gate and Mara refusing to step forward.",
            "bloom_level": "analyze",
        }

        is_allowed = _question_matches_current_concept(
            question,
            concept_name="Interpretation questions",
            concept_summary="[Literary Toolkit] Practice explaining what the text means.",
            tutor_explanation="The moment suggests hesitation and tension around the open gate.",
            tutor_examples=["The open gate can symbolize a choice."],
            locked_concept_titles=["Later revelation"],
            allowed_bloom_levels=["analyze"],
        )

        self.assertTrue(is_allowed)

    def test_short_answer_question_is_rejected_for_non_literary_concepts(self) -> None:
        question = {
            "question_type": "short_answer",
            "question_text": "Explain decimals using evidence.",
            "options": {"A": "", "B": "", "C": "", "D": ""},
            "correct_option": "",
            "explanation": "Decimals use place value.",
            "expected_answer": "Decimals use place value after a decimal point.",
            "evidence_guidance": "Use the place value sentence.",
            "bloom_level": "analyze",
        }

        is_allowed = _question_matches_current_concept(
            question,
            concept_name="Decimals",
            concept_summary="Decimals use place value after a decimal point.",
            tutor_explanation="Decimals use place value after a decimal point.",
            tutor_examples=["0.5 is five tenths."],
            locked_concept_titles=[],
            allowed_bloom_levels=["analyze"],
        )

        self.assertFalse(is_allowed)

    def test_mcq_prompt_requests_latex_for_math_expressions(self) -> None:
        prompt = build_mcq_input(
            concept_id=self.current_concept.id,
            concept_name="Fractions",
            concept_summary="Compare parts of a whole.",
            source_excerpt="One half can be written as 1/2.",
            tutor_explanation="A fraction compares a part to a whole.",
            tutor_examples=["1/2 means one out of two equal parts."],
            question_count=2,
            attempt_mode=FIRST_ATTEMPT,
            bloom_distribution={"remember": 1, "understand": 1},
        )

        self.assertIn("Inline math must use \\( ... \\)", MCQ_INSTRUCTIONS)
        self.assertIn("Block equations must use \\[ ... \\]", MCQ_INSTRUCTIONS)
        self.assertIn("\\times", MCQ_INSTRUCTIONS)
        self.assertIn("question text, options, or explanations include math", prompt)
        self.assertIn("format only mathematical expressions in LaTeX", prompt)

    def test_bloom_distribution_matches_first_attempt_goal(self) -> None:
        distribution = _bloom_distribution_for_attempt(FIRST_ATTEMPT, question_count=5)

        basic_count = distribution["remember"] + distribution["understand"]
        stronger_count = distribution["apply"] + distribution["analyze"]
        self.assertEqual(basic_count, 3)
        self.assertEqual(stronger_count, 2)
        self.assertNotIn("evaluate", distribution)

    def test_bloom_distribution_matches_reinforcement_goal(self) -> None:
        distribution = _bloom_distribution_for_attempt(REINFORCEMENT_ATTEMPT, question_count=5)

        basic_count = distribution["remember"] + distribution["understand"]
        stronger_count = distribution["apply"] + distribution["analyze"] + distribution["evaluate"]
        self.assertEqual(basic_count, 2)
        self.assertEqual(stronger_count, 3)
        self.assertIn("evaluate", distribution)

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_returns_existing_unanswered_mcqs_without_regenerating(self, mock_generate) -> None:
        existing_question = QuizQuestion.objects.create(
            concept=self.current_concept,
            question_text="Existing question?",
            option_a="A",
            option_b="B",
            option_c="C",
            option_d="D",
            correct_option="A",
            explanation="Existing explanation.",
        )

        questions = get_or_generate_current_concept_mcqs(self.user, self.document)

        self.assertEqual(questions, [existing_question])
        mock_generate.assert_not_called()


class MCQApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-mcq-student",
            email="api-mcq-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            owner=self.user,
            title="API MCQ Course",
            file=SimpleUploadedFile("api-mcq.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Cells",
            sequence_number=1,
            extracted_text="Cells are the basic unit of life.",
        )
        self.concept = Concept.objects.create(
            chapter=self.chapter,
            title="Cells",
            sequence_number=1,
            summary="Cells are the basic unit of life.",
        )
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept,
            source_excerpt="Cells are the basic unit of life.",
            explanation="Cells are the basic unit of life.",
            examples=["A skin cell is one kind of cell."],
            next_action="ready_for_mcq",
        )

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_current_mcq_endpoint_returns_student_safe_questions(self, mock_generate) -> None:
        mock_generate.return_value = [
            {
                "question_text": "What are cells?",
                "options": {
                    "A": "The basic unit of life",
                    "B": "A kind of telescope",
                    "C": "A type of cloud",
                    "D": "A punctuation mark",
                },
                "correct_option": "A",
                "explanation": "Cells are commonly described as the basic unit of life.",
                "bloom_level": "remember",
            }
        ]

        response = self.client.get(reverse("current-concept-mcqs", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["questions"][0]["concept_id"], self.concept.id)
        self.assertEqual(response.data["questions"][0]["bloom_level"], "remember")
        self.assertEqual(response.data["questions"][0]["question_text"], "What are cells?")
        self.assertEqual(set(response.data["questions"][0]["options"].keys()), {"A", "B", "C", "D"})
        self.assertNotIn("correct_option", response.data["questions"][0])
        self.assertNotIn("explanation", response.data["questions"][0])

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_current_mcq_endpoint_supports_student_safe_short_answer_checks(self, mock_generate) -> None:
        self.concept.summary = "[Literary Toolkit] Interpret the current section."
        self.concept.save(update_fields=["summary"])
        ConceptLesson.objects.filter(user=self.user, concept=self.concept).update(
            source_excerpt="The dark image creates an uneasy mood.",
            explanation="The dark image creates an uneasy mood in the current section.",
            examples=["A shadow can make a scene feel tense."],
        )
        mock_generate.return_value = [
            {
                "question_type": "short_answer",
                "question_text": "How does the quoted image create mood?",
                "options": {"A": "", "B": "", "C": "", "D": ""},
                "correct_option": "",
                "explanation": "A strong answer connects the image to mood.",
                "expected_answer": "The image creates an uneasy mood through dark details.",
                "evidence_guidance": "Use the image from the current section.",
                "bloom_level": "analyze",
            }
        ]

        response = self.client.get(reverse("current-concept-mcqs", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        question = response.data["questions"][0]
        self.assertEqual(question["question_type"], "short_answer")
        self.assertEqual(question["options"], {})
        self.assertIn("evidence_guidance", question)
        self.assertNotIn("expected_answer", question)
        self.assertNotIn("correct_option", question)

    @patch("learning.mcq._generate_mcqs_with_openai")
    def test_current_mcq_endpoint_returns_clean_error_when_openai_rejects_request(self, mock_generate) -> None:
        mock_generate.side_effect = OpenAIServiceError("OpenAI rejected the configured API key.", status_code=401)

        response = self.client.get(reverse("current-concept-mcqs", kwargs={"document_id": self.document.id}))

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data["detail"], "OpenAI rejected the configured API key.")


class QuizGradingServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="grading-student",
            email="grading-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Grading Course",
            file=SimpleUploadedFile("grading.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Ratios", sequence_number=1)
        self.current_concept = Concept.objects.create(chapter=self.chapter, title="Ratios", sequence_number=1)
        self.next_concept = Concept.objects.create(chapter=self.chapter, title="Unit Rates", sequence_number=2)
        self.question_1 = QuizQuestion.objects.create(
            concept=self.current_concept,
            question_text="What is a ratio?",
            option_a="A comparison of two quantities",
            option_b="A type of map",
            option_c="A punctuation mark",
            option_d="A random number",
            correct_option="A",
            bloom_level=BloomLevel.REMEMBER,
            explanation="A ratio compares two quantities.",
        )
        self.question_2 = QuizQuestion.objects.create(
            concept=self.current_concept,
            question_text="Which is a ratio?",
            option_a="Blue",
            option_b="3 to 2",
            option_c="Yesterday",
            option_d="Triangle",
            correct_option="B",
            bloom_level=BloomLevel.APPLY,
            explanation="3 to 2 compares two quantities.",
        )

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_passing_attempt_marks_concept_mastered_and_unlocks_next_concept(self) -> None:
        attempt = submit_current_concept_answers(
            self.user,
            self.document,
            {str(self.question_1.id): "A", str(self.question_2.id): "B"},
        )

        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.score, 100)
        self.assertEqual(QuizAttempt.objects.count(), 1)
        attempt.refresh_from_db()
        self.assertEqual(attempt.bloom_level_scores, {"remember": "100.00", "apply": "100.00"})
        mastery = ConceptMastery.objects.get(user=self.user, concept=self.current_concept)
        self.assertEqual(
            mastery.bloom_level_scores,
            {"remember": "100.00", "apply": "100.00"},
        )
        self.assertEqual(mastery.mastery_score, Decimal("100.00"))
        self.assertEqual(mastery.mastery_strength, MasteryStrength.SLOW)
        self.assertIsNotNone(mastery.last_reviewed_at)
        self.assertIsNotNone(mastery.next_review_at)
        self.assertEqual(mastery.forgetting_rate, Decimal("0.03333"))
        self.assertTrue(QuizQuestion.objects.get(id=self.question_1.id).is_answered)
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.current_concept).status,
            ProgressStatus.MASTERED,
        )
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.next_concept).status,
            ProgressStatus.UNLOCKED,
        )

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_failing_attempt_saves_remediation_and_does_not_unlock_next_concept(self) -> None:
        attempt = submit_current_concept_answers(
            self.user,
            self.document,
            {str(self.question_1.id): "A", str(self.question_2.id): "A"},
        )

        self.assertFalse(attempt.passed)
        self.assertEqual(attempt.score, 50)
        self.assertEqual(attempt.bloom_level_scores, {"remember": "100.00", "apply": "0.00"})
        mastery = ConceptMastery.objects.get(user=self.user, concept=self.current_concept)
        self.assertEqual(mastery.mastery_score, Decimal("50.00"))
        self.assertEqual(mastery.mastery_strength, MasteryStrength.FAST)
        self.assertIn("Review this concept", attempt.remediation)
        self.assertIn("3 to 2 compares two quantities", attempt.remediation)
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.current_concept).status,
            ProgressStatus.UNLOCKED,
        )
        self.assertEqual(
            ConceptProgress.objects.get(user=self.user, concept=self.next_concept).status,
            ProgressStatus.LOCKED,
        )
        serialized_attempt = QuizAttemptResultSerializer(attempt).data
        self.assertFalse(serialized_attempt["passed"])
        self.assertEqual(serialized_attempt["remediation_message"], "You did not pass this check yet. Choose how you want to continue.")
        self.assertEqual(serialized_attempt["available_actions"], ["ask_tutor", "restart_concept", "retry_quiz"])

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_literary_short_answer_accepts_supported_interpretation(self) -> None:
        QuizQuestion.objects.filter(concept=self.current_concept).delete()
        self.current_concept.title = "Interpretation questions"
        self.current_concept.summary = "[Literary Toolkit] Practice explaining what the text means."
        self.current_concept.save(update_fields=["title", "summary"])
        question = QuizQuestion.objects.create(
            concept=self.current_concept,
            question_type=QuizQuestionType.SHORT_ANSWER,
            question_text="How does the open gate help create tension?",
            bloom_level=BloomLevel.ANALYZE,
            explanation="A strong answer connects the open gate to hesitation and choice.",
            expected_answer="The gate suggests a choice, while hesitation creates tension.",
            evidence_guidance="Use the open gate and the character refusing to step forward.",
        )

        attempt = submit_current_concept_answers(
            self.user,
            self.document,
            {str(question.id): "The open gate suggests a choice, and the character's hesitation creates tension because she refuses to move forward."},
        )

        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.score, Decimal("100.00"))
        self.assertEqual(attempt.bloom_level_scores, {"analyze": "100.00"})

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_literary_short_answer_rejects_unsupported_or_tiny_answer(self) -> None:
        QuizQuestion.objects.filter(concept=self.current_concept).delete()
        question = QuizQuestion.objects.create(
            concept=self.current_concept,
            question_type=QuizQuestionType.SHORT_ANSWER,
            question_text="What theme is suggested here?",
            bloom_level=BloomLevel.ANALYZE,
            explanation="The answer should connect a theme to evidence.",
            expected_answer="The section suggests fear through the character's hesitation.",
            evidence_guidance="Use evidence about hesitation.",
        )

        attempt = submit_current_concept_answers(
            self.user,
            self.document,
            {str(question.id): "fear"},
        )

        self.assertFalse(attempt.passed)
        self.assertEqual(attempt.score, Decimal("0.00"))


class ForgettingCurveServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="forgetting-student",
            email="forgetting-student@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Retention Course",
            file=SimpleUploadedFile("retention.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Memory", sequence_number=1)
        self.concept = Concept.objects.create(chapter=self.chapter, title="Retention", sequence_number=1)

    def test_calculates_decayed_mastery_from_review_time_and_strength(self) -> None:
        reviewed_at = timezone.now() - timedelta(days=7)
        mastery = ConceptMastery.objects.create(
            user=self.user,
            concept=self.concept,
            mastery_score=Decimal("90.00"),
            mastery_strength=MasteryStrength.SLOW,
            last_reviewed_at=reviewed_at,
            forgetting_rate=Decimal("0.03333"),
        )

        decayed_score = calculate_decayed_mastery(mastery, reviewed_at + timedelta(days=7))

        self.assertEqual(decayed_score, Decimal("71.27"))

    def test_weaker_mastery_decays_faster_than_stronger_mastery(self) -> None:
        reviewed_at = timezone.now() - timedelta(days=7)
        weak_mastery = ConceptMastery.objects.create(
            user=self.user,
            concept=self.concept,
            mastery_score=Decimal("90.00"),
            mastery_strength=MasteryStrength.FAST,
            last_reviewed_at=reviewed_at,
        )
        strong_mastery = ConceptMastery(
            user=self.user,
            concept=self.concept,
            mastery_score=Decimal("90.00"),
            mastery_strength=MasteryStrength.SLOW,
            last_reviewed_at=reviewed_at,
        )

        self.assertLess(
            calculate_decayed_mastery(weak_mastery, reviewed_at + timedelta(days=7)),
            calculate_decayed_mastery(strong_mastery, reviewed_at + timedelta(days=7)),
        )


class StudentAIMemoryServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="student-ai-user",
            email="student-ai@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Student AI Course",
            file=SimpleUploadedFile("student-ai.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Markets", sequence_number=1)
        self.concept = Concept.objects.create(chapter=self.chapter, title="Supply", sequence_number=1)

    def test_teaching_student_ai_memory_stores_retention_metadata(self) -> None:
        memory = teach_student_ai_memory(
            self.user,
            self.concept,
            taught_content="Supply is how much sellers are willing to offer at a price.",
            initial_mastery_score=Decimal("92"),
        )

        self.assertEqual(memory.concept, self.concept)
        self.assertEqual(memory.initial_mastery_score, Decimal("92.00"))
        self.assertEqual(memory.current_retention_score, Decimal("92.00"))
        self.assertEqual(memory.retention_strength, MasteryStrength.SLOW)
        self.assertIsNotNone(memory.taught_at)
        self.assertIsNotNone(memory.next_review_at)
        self.assertIsNone(memory.last_spot_quiz_at)

    def test_student_ai_retention_decays_from_human_taught_content_time(self) -> None:
        taught_at = timezone.now() - timedelta(days=7)
        memory = StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Supply is how much sellers offer.",
            taught_at=taught_at,
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
        )

        self.assertEqual(calculate_student_ai_retention(memory, taught_at + timedelta(days=7)), Decimal("71.27"))

    @patch("learning.student_ai._answer_with_openai")
    def test_student_ai_answer_uses_decayed_retention_and_updates_spot_quiz_time(self, mock_answer) -> None:
        StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Supply is how much sellers offer.",
            taught_at=timezone.now() - timedelta(days=7),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
        )
        mock_answer.return_value = {
            "concept_id": self.concept.id,
            "question": "What is supply?",
            "answer": "Supply is how much sellers offer.",
            "retention_level": "medium",
            "current_retention_score": "71.27",
        }

        answer = answer_student_ai_question(self.user, self.concept, "What is supply?")

        self.assertEqual(answer["answer"], "Supply is how much sellers offer.")
        kwargs = mock_answer.call_args.kwargs
        self.assertEqual(kwargs["taught_content"], "Supply is how much sellers offer.")
        self.assertNotIn("source_excerpt", kwargs)
        memory = StudentAIMemory.objects.get(user=self.user, concept=self.concept)
        self.assertIsNotNone(memory.last_spot_quiz_at)
        self.assertLess(memory.current_retention_score, Decimal("90.00"))

    def test_student_ai_prompt_blocks_source_material_and_general_knowledge(self) -> None:
        prompt = build_student_ai_answer_input(
            concept_id=self.concept.id,
            concept_name=self.concept.title,
            taught_content="Supply is how much sellers offer.",
            current_retention_score="55.00",
            retention_strength="fast",
            question="What is supply?",
        )

        self.assertIn("Human-taught content only", prompt)
        self.assertIn("Do not use textbook/source material directly", prompt)
        self.assertIn("Do not add facts that were not taught by the human student", prompt)


class StudentAIMemoryApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-student-ai-user",
            email="api-student-ai@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.subject = Subject.objects.create(owner=self.user, name="Economics")
        self.other_subject = Subject.objects.create(owner=self.user, name="Literature")
        self.document = Document.objects.create(
            owner=self.user,
            subject=self.subject,
            title="API Student AI Course",
            file=SimpleUploadedFile("api-student-ai.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Demand", sequence_number=1)
        self.concept = Concept.objects.create(chapter=self.chapter, title="Demand", sequence_number=1)
        ConceptProgress.objects.create(user=self.user, concept=self.concept, status=ProgressStatus.MASTERED)

    def test_teach_student_ai_memory_endpoint(self) -> None:
        response = self.client.post(
            reverse("student-ai-memory-teach"),
            {
                "concept_id": self.concept.id,
                "taught_content": "Demand is how much buyers want at a price.",
                "initial_mastery_score": "82.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["concept_id"], self.concept.id)
        self.assertEqual(response.data["retention_strength"], MasteryStrength.MEDIUM)
        self.assertEqual(StudentAIMemory.objects.count(), 1)

    def test_teach_student_ai_memory_rejects_mismatched_subject(self) -> None:
        response = self.client.post(
            reverse("student-ai-memory-teach"),
            {
                "concept_id": self.concept.id,
                "subject_id": self.other_subject.id,
                "taught_content": "Demand is how much buyers want at a price.",
                "initial_mastery_score": "82.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(StudentAIMemory.objects.count(), 0)

    def test_teach_student_ai_memory_requires_passed_concept(self) -> None:
        future_concept = Concept.objects.create(chapter=self.chapter, title="Future demand", sequence_number=2)
        ConceptProgress.objects.create(user=self.user, concept=future_concept, status=ProgressStatus.LOCKED)

        response = self.client.post(
            reverse("student-ai-memory-teach"),
            {
                "concept_id": future_concept.id,
                "taught_content": "This concept has not been passed yet.",
                "initial_mastery_score": "82.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(StudentAIMemory.objects.filter(concept=future_concept).count(), 0)

    @patch("learning.student_ai._answer_with_openai")
    def test_student_ai_ask_endpoint_answers_from_memory(self, mock_answer) -> None:
        StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Demand is how much buyers want at a price.",
            taught_at=timezone.now(),
            initial_mastery_score=Decimal("82.00"),
            current_retention_score=Decimal("82.00"),
            retention_strength=MasteryStrength.MEDIUM,
        )
        mock_answer.return_value = {
            "concept_id": self.concept.id,
            "question": "What is demand?",
            "answer": "Demand is how much buyers want at a price.",
            "retention_level": "medium",
            "current_retention_score": "82.00",
        }

        response = self.client.post(
            reverse("student-ai-ask"),
            {"concept_id": self.concept.id, "question": "What is demand?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["retention_level"], "medium")
        self.assertEqual(response.data["answer"], "Demand is how much buyers want at a price.")

    @patch("learning.student_ai._answer_with_openai")
    def test_student_ai_ask_rejects_mismatched_subject(self, mock_answer) -> None:
        StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Demand is how much buyers want at a price.",
            taught_at=timezone.now(),
            initial_mastery_score=Decimal("82.00"),
            current_retention_score=Decimal("82.00"),
            retention_strength=MasteryStrength.MEDIUM,
        )

        response = self.client.post(
            reverse("student-ai-ask"),
            {
                "concept_id": self.concept.id,
                "subject_id": self.other_subject.id,
                "question": "What is demand?",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_answer.assert_not_called()

    @patch("learning.views.process_student_ai_spot_quiz")
    def test_student_ai_examiner_check_returns_celebration_when_ariel_passes(self, mock_process) -> None:
        memory = StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Demand is how much buyers want at a price.",
            taught_at=timezone.now(),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
        )
        attempt = StudentAISpotQuizAttempt.objects.create(
            user=self.user,
            concept=self.concept,
            memory=memory,
            question="What is demand?",
            student_ai_answer="Demand is what buyers want at a price.",
            score=Decimal("92.00"),
            passed=True,
            feedback="Ariel remembered the key idea.",
            retention_score_at_quiz=Decimal("90.00"),
        )
        mock_process.return_value = attempt

        response = self.client.post(
            reverse("student-ai-examiner-check"),
            {"concept_id": self.concept.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["passed"])
        self.assertEqual(response.data["celebration"], "ariel_examiner_passed")

    @patch("learning.views.process_student_ai_spot_quiz")
    def test_student_ai_examiner_check_rejects_mismatched_subject(self, mock_process) -> None:
        StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Demand is how much buyers want at a price.",
            taught_at=timezone.now(),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
        )

        response = self.client.post(
            reverse("student-ai-examiner-check"),
            {"concept_id": self.concept.id, "subject_id": self.other_subject.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_process.assert_not_called()

    @patch("learning.views.process_student_ai_spot_quiz")
    def test_student_ai_examiner_check_requires_completed_chapter(self, mock_process) -> None:
        future_concept = Concept.objects.create(chapter=self.chapter, title="Future demand", sequence_number=2)
        ConceptProgress.objects.create(user=self.user, concept=future_concept, status=ProgressStatus.UNLOCKED)
        StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Demand is how much buyers want at a price.",
            taught_at=timezone.now(),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
        )

        response = self.client.post(
            reverse("student-ai-examiner-check"),
            {"concept_id": self.concept.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_process.assert_not_called()


class StudentAISpotQuizServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="spot-quiz-user",
            email="spot-quiz@example.com",
            password="test-password",
        )
        self.document = Document.objects.create(
            owner=self.user,
            title="Spot Quiz Course",
            file=SimpleUploadedFile("spot-quiz.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Inflation",
            sequence_number=1,
            extracted_text="Inflation is a sustained rise in the general price level.",
        )
        self.concept = Concept.objects.create(
            chapter=self.chapter,
            title="Inflation",
            sequence_number=1,
            summary="Inflation means prices rise over time.",
        )
        ConceptProgress.objects.create(user=self.user, concept=self.concept, status=ProgressStatus.MASTERED)
        ConceptLesson.objects.create(
            user=self.user,
            concept=self.concept,
            source_excerpt="Inflation is a sustained rise in the general price level.",
            explanation="Inflation means the overall price level rises over time.",
            examples=["If many prices rise together, purchasing power falls."],
            next_action="ready_for_mcq",
        )

    @override_settings(STUDENT_AI_RETENTION_REVIEW_THRESHOLD=75)
    def test_due_memory_requires_completed_concept_low_retention_and_due_review(self) -> None:
        current_time = timezone.now()
        due_memory = StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Inflation means prices rise over time.",
            taught_at=current_time - timedelta(days=7),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
            next_review_at=current_time - timedelta(minutes=1),
        )
        future_memory = StudentAIMemory.objects.create(
            user=get_user_model().objects.create_user(username="future-memory"),
            concept=self.concept,
            taught_content="Future memory.",
            taught_at=current_time,
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
            next_review_at=current_time + timedelta(days=1),
        )

        due_memories = due_student_ai_memories(current_time)

        self.assertIn(due_memory, due_memories)
        self.assertNotIn(future_memory, due_memories)

    @patch("learning.spot_quiz.grade_student_ai_spot_answer")
    @patch("learning.spot_quiz._answer_with_openai")
    @patch("learning.spot_quiz.generate_spot_quiz_question")
    def test_failed_spot_quiz_creates_daily_reinforcement_report(self, mock_question, mock_answer, mock_grade) -> None:
        current_time = timezone.now()
        memory = StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Inflation means prices rise.",
            taught_at=current_time - timedelta(days=7),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
            next_review_at=current_time - timedelta(minutes=1),
        )
        mock_question.return_value = "What is inflation?"
        mock_answer.return_value = {
            "concept_id": self.concept.id,
            "question": "What is inflation?",
            "answer": "Prices.",
            "retention_level": "medium",
            "current_retention_score": "71.27",
        }
        mock_grade.return_value = {"score": 40, "passed": False, "feedback": "The answer is too vague."}

        attempt = process_student_ai_spot_quiz(memory, current_time)

        self.assertFalse(attempt.passed)
        self.assertEqual(StudentAISpotQuizAttempt.objects.count(), 1)
        report = StudentAIReinforcementReport.objects.get(user=self.user, report_date=current_time.date())
        self.assertEqual(len(report.recommendations), 1)
        self.assertEqual(report.recommendations[0]["concept_id"], self.concept.id)
        recommendation = ReinforcementRecommendation.objects.get(user=self.user, concept=self.concept)
        self.assertIn("Ariel scored 40.00%", recommendation.reason)
        self.assertEqual(recommendation.failed_bloom_level, BloomLevel.UNDERSTAND)
        self.assertEqual(recommendation.student_ai_score, Decimal("40.00"))
        self.assertEqual(recommendation.recommended_action, "Teach Ariel")
        self.assertEqual(recommendation.friendly_label, "Ariel is getting rusty")
        self.assertIn("Give it a quick refresher lesson", recommendation.friendly_message)
        self.assertEqual(recommendation.mission_title, "Rescue mission: reteach Inflation")
        self.assertEqual(recommendation.priority, RecommendationPriority.HIGH)
        self.assertIsNone(recommendation.resolved_at)
        memory.refresh_from_db()
        self.assertEqual(memory.next_review_at.date(), (current_time + timedelta(days=1)).date())
        self.assertEqual(mock_answer.call_args.kwargs["taught_content"], "Inflation means prices rise.")
        self.assertNotIn("official_material", mock_answer.call_args.kwargs)

    @patch("learning.spot_quiz.process_student_ai_spot_quiz")
    def test_periodic_runner_processes_due_memories(self, mock_process) -> None:
        current_time = timezone.now()
        memory = StudentAIMemory.objects.create(
            user=self.user,
            concept=self.concept,
            taught_content="Inflation means prices rise over time.",
            taught_at=current_time - timedelta(days=7),
            initial_mastery_score=Decimal("90.00"),
            current_retention_score=Decimal("90.00"),
            retention_strength=MasteryStrength.SLOW,
            next_review_at=current_time - timedelta(minutes=1),
        )

        processed_count = run_due_student_ai_spot_quizzes(current_time)

        self.assertEqual(processed_count, 1)
        mock_process.assert_called_once_with(memory, current_time)


class QuizSubmissionApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="api-grading-student",
            email="api-grading-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.document = Document.objects.create(
            owner=self.user,
            title="API Grading Course",
            file=SimpleUploadedFile("api-grading.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter = Chapter.objects.create(document=self.document, title="Energy", sequence_number=1)
        self.concept = Concept.objects.create(chapter=self.chapter, title="Energy", sequence_number=1)
        self.question = QuizQuestion.objects.create(
            concept=self.concept,
            question_text="What is energy?",
            option_a="Ability to do work",
            option_b="A color",
            option_c="A planet",
            option_d="A letter",
            correct_option="A",
            bloom_level=BloomLevel.UNDERSTAND,
            explanation="Energy is often defined as the ability to do work.",
        )

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_submit_answers_endpoint_returns_attempt_result(self) -> None:
        response = self.client.post(
            reverse("submit-current-concept-mcqs", kwargs={"document_id": self.document.id}),
            {"answers": {str(self.question.id): "A"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["passed"])
        self.assertEqual(response.data["bloom_level_scores"], {"understand": "100.00"})
        self.assertEqual(response.data["correct_answers"], 1)
        self.assertEqual(response.data["next_action"], "next_concept_unlocked")
        self.assertEqual(response.data["celebration"], "document_completed")

    @override_settings(QUIZ_PASSING_THRESHOLD=80)
    def test_submit_answers_endpoint_marks_mid_document_chapter_completion(self) -> None:
        next_chapter = Chapter.objects.create(document=self.document, title="Forces", sequence_number=2)
        Concept.objects.create(chapter=next_chapter, title="Force", sequence_number=1)

        response = self.client.post(
            reverse("submit-current-concept-mcqs", kwargs={"document_id": self.document.id}),
            {"answers": {str(self.question.id): "A"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["passed"])
        self.assertEqual(response.data["celebration"], "chapter_completed")


class ProgressDashboardTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="dashboard-student",
            email="dashboard-student@example.com",
            password="test-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.subject = Subject.objects.create(owner=self.user, name="Dashboard Subject")
        self.other_subject = Subject.objects.create(owner=self.user, name="Other Subject")
        self.document = Document.objects.create(
            owner=self.user,
            subject=self.subject,
            title="Dashboard Course",
            file=SimpleUploadedFile("dashboard.pdf", b"fake pdf content", content_type="application/pdf"),
        )
        self.chapter_2 = Chapter.objects.create(document=self.document, title="Second", sequence_number=2)
        self.chapter_1 = Chapter.objects.create(document=self.document, title="First", sequence_number=1)
        self.concept_2 = Concept.objects.create(chapter=self.chapter_1, title="Second Concept", sequence_number=2)
        self.concept_1 = Concept.objects.create(chapter=self.chapter_1, title="First Concept", sequence_number=1)
        self.concept_3 = Concept.objects.create(chapter=self.chapter_2, title="Third Concept", sequence_number=1)

    def test_dashboard_uses_database_order_and_percentages(self) -> None:
        mark_concept_mastered(self.user, self.concept_1)
        ConceptMastery.objects.create(
            user=self.user,
            concept=self.concept_1,
            mastery_score=Decimal("100.00"),
            mastery_strength=MasteryStrength.SLOW,
            last_reviewed_at=timezone.now(),
            next_review_at=timezone.now() + timedelta(days=30),
            forgetting_rate=Decimal("0.03333"),
            bloom_level_scores={"remember": "100.00"},
        )
        QuizAttempt.objects.create(
            user=self.user,
            concept=self.concept_2,
            submitted_answers={},
            total_questions=1,
            correct_answers=0,
            score=0,
            passed=False,
            bloom_level_scores={"understand": "0.00"},
            remediation="Review the second concept.",
        )

        dashboard = build_progress_dashboard(self.user, subject_id=self.subject.id)
        document = dashboard["documents"][0]

        self.assertEqual(document["completion_percentage"], "33.33")
        self.assertEqual([chapter["title"] for chapter in document["chapters"]], ["First", "Second"])
        self.assertEqual(document["chapters"][0]["completion_percentage"], "50.00")
        self.assertEqual(
            [concept["title"] for concept in document["chapters"][0]["concepts"]],
            ["First Concept", "Second Concept"],
        )
        self.assertEqual(document["chapters"][0]["concepts"][0]["status"], "passed")
        self.assertEqual(document["chapters"][0]["concepts"][0]["mastery_score"], "100.00")
        self.assertEqual(document["chapters"][0]["concepts"][0]["decayed_mastery_score"], "100.00")
        self.assertEqual(document["chapters"][0]["concepts"][0]["mastery_strength"], "slow")
        self.assertEqual(document["chapters"][0]["concepts"][1]["status"], "failed")
        self.assertEqual(document["chapters"][1]["concepts"][0]["status"], "locked")
        self.assertEqual(document["current_recommended_next_action"], "start_current_concept")

    def test_dashboard_shows_student_ai_reinforcement_recommendations(self) -> None:
        recommendation = ReinforcementRecommendation.objects.create(
            user=self.user,
            concept=self.concept_1,
            reason="Ariel is forgetting this concept.",
            failed_bloom_level=BloomLevel.APPLY,
            student_ai_score=Decimal("62.00"),
            recommended_action="Try an apply-level question",
            friendly_label="Practice boost ready",
            friendly_message="Ariel is starting to forget this concept.",
            mission_title="Rescue mission: reteach First Concept",
            priority=RecommendationPriority.MEDIUM,
        )

        dashboard = build_progress_dashboard(self.user, subject_id=self.subject.id)
        reinforcement = dashboard["student_ai_reinforcement"]
        memory_engine = dashboard["teachback_memory_engine"]

        self.assertEqual(reinforcement["headline"], "Ariel is getting rusty on these concepts.")
        self.assertEqual(len(reinforcement["recommendations"]), 1)
        self.assertEqual(reinforcement["recommendations"][0]["id"], recommendation.id)
        self.assertEqual(reinforcement["recommendations"][0]["concept_title"], "First Concept")
        self.assertEqual(reinforcement["recommendations"][0]["recommended_action"], "Try an apply-level question")
        self.assertEqual(memory_engine["feature_name"], "TeachBack Memory Engine")
        self.assertEqual(memory_engine["memory_health"]["score"], "62.00")
        self.assertEqual(memory_engine["daily_rescue_missions"][0]["mission_title"], "Rescue mission: reteach First Concept")
        self.assertEqual(memory_engine["bloom_mastery_badges"][0]["label"], "Application Ace")

    def test_dashboard_endpoint_returns_uploaded_documents_from_database(self) -> None:
        response = self.client.get(reverse("progress-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["documents"][0]["document_id"], self.document.id)
        self.assertEqual(response.data["documents"][0]["title"], "Dashboard Course")
        self.assertEqual(response.data["documents"][0]["current_concept_title"], "First Concept")
        self.assertEqual(response.data["documents"][0]["chapters"], [])

    def test_dashboard_endpoint_returns_full_tree_when_subject_scoped(self) -> None:
        response = self.client.get(reverse("progress-dashboard"), {"subject": self.subject.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["documents"]), 1)
        self.assertEqual([chapter["sequence_number"] for chapter in response.data["documents"][0]["chapters"]], [1, 2])

    def test_dashboard_endpoint_filters_by_subject(self) -> None:
        Document.objects.create(
            owner=self.user,
            subject=self.other_subject,
            title="Other Course",
            file=SimpleUploadedFile("other.pdf", b"fake pdf content", content_type="application/pdf"),
        )

        response = self.client.get(reverse("progress-dashboard"), {"subject": self.subject.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([document["title"] for document in response.data["documents"]], ["Dashboard Course"])

    def test_dashboard_does_not_treat_missing_concepts_as_complete(self) -> None:
        Concept.objects.filter(chapter__document=self.document).delete()
        self.document.status = "processing_concepts"
        self.document.save(update_fields=["status"])

        dashboard = build_progress_dashboard(self.user, subject_id=self.subject.id)
        document = dashboard["documents"][0]

        self.assertEqual(document["concept_count"], 0)
        self.assertEqual(document["current_recommended_next_action"], "wait_for_concepts")

    def test_dashboard_flags_ready_document_with_no_concepts(self) -> None:
        Concept.objects.filter(chapter__document=self.document).delete()
        self.document.status = "ready"
        self.document.save(update_fields=["status"])

        dashboard = build_progress_dashboard(self.user, subject_id=self.subject.id)
        document = dashboard["documents"][0]

        self.assertEqual(document["concept_count"], 0)
        self.assertEqual(document["current_recommended_next_action"], "concepts_missing")
