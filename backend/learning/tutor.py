import json
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from documents.models import Document
from documents.parsing.literary_toolkit import is_literary_summary

from .concept_context import build_concept_source_excerpt
from .models import ConceptLesson, ProgressStatus, QuizQuestion, TutorMessage
from .openai_client import call_openai_responses_api, extract_output_text
from .prompts import (
    TUTOR_ANSWER_INSTRUCTIONS,
    TUTOR_ANSWER_RESPONSE_SCHEMA,
    TUTOR_INSTRUCTIONS,
    TUTOR_RESPONSE_SCHEMA,
    build_tutor_answer_input,
    build_tutor_input,
)
from .services import get_current_unlocked_concept


def teach_current_unlocked_concept(user, document: Document) -> dict | None:
    """Generate a structured lesson for the student's current unlocked concept."""

    current = get_current_unlocked_concept(user, document)
    if current is None:
        return None

    concept = current.concept
    source_excerpt = build_concept_source_excerpt(concept)
    literary_metadata = _literary_metadata_for_concept(concept)
    lesson = _generate_lesson_with_openai(
        concept_id=concept.id,
        concept_name=concept.title,
        concept_summary=concept.summary,
        source_excerpt=source_excerpt,
        literary_metadata=literary_metadata,
    )
    lesson["is_literary"] = bool(literary_metadata)
    lesson["literary_metadata"] = literary_metadata
    ConceptLesson.objects.update_or_create(
        user=user,
        concept=concept,
        defaults={
            "source_excerpt": source_excerpt,
            "explanation": lesson["explanation"],
            "examples": lesson["examples"],
            "visual_content": lesson.get("visual_content") or {},
            "next_action": lesson["next_action"],
        },
    )
    QuizQuestion.objects.filter(concept=concept, is_answered=False).delete()

    if current.progress.status == ProgressStatus.UNLOCKED:
        current.progress.status = ProgressStatus.IN_PROGRESS
        current.progress.save(update_fields=["status", "updated_at"])

    return lesson


def answer_current_concept_question(user, document: Document, *, concept_id: int, question: str) -> dict:
    current = get_current_unlocked_concept(user, document)
    if current is None or current.concept.id != concept_id:
        raise ValueError("Questions can only be asked about the currently unlocked concept.")

    lesson = ConceptLesson.objects.filter(user=user, concept=current.concept).first()
    if lesson is None:
        raise ValueError("Teach the current concept before asking follow-up questions.")

    answer = _answer_question_with_openai(
        concept_id=current.concept.id,
        concept_name=current.concept.title,
        concept_summary=current.concept.summary,
        source_excerpt=lesson.source_excerpt,
        chapter_objectives=current.concept.chapter.chapter_objectives,
        literary_metadata=_literary_metadata_for_concept(current.concept),
        lesson_explanation=lesson.explanation,
        lesson_examples=lesson.examples,
        student_question=question,
    )
    TutorMessage.objects.create(
        user=user,
        concept=current.concept,
        student_question=answer["student_question"],
        tutor_answer=answer["tutor_answer"],
        visual_content=answer.get("visual_content") or {},
        source_mode=answer["source_mode"],
    )
    return answer


def _generate_lesson_with_openai(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str,
    source_excerpt: str,
    literary_metadata: dict | None = None,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise ImproperlyConfigured("OPENAI_API_KEY is required to generate The Abbot lessons.")

    payload = {
        "model": settings.OPENAI_TUTOR_MODEL,
        "instructions": TUTOR_INSTRUCTIONS,
        "input": build_tutor_input(
            concept_id=concept_id,
            concept_name=concept_name,
            concept_summary=concept_summary,
            source_excerpt=source_excerpt,
            literary_metadata=literary_metadata,
        ),
        "text": {"format": TUTOR_RESPONSE_SCHEMA},
    }

    api_response = call_openai_responses_api(payload)
    lesson = json.loads(extract_output_text(api_response))
    lesson = _normalize_lesson(lesson)
    lesson["concept_id"] = concept_id
    lesson["concept_name"] = concept_name
    return lesson


def _answer_question_with_openai(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str,
    source_excerpt: str,
    chapter_objectives: list[str],
    literary_metadata: dict | None = None,
    lesson_explanation: str,
    lesson_examples: list[str],
    student_question: str,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise ImproperlyConfigured("OPENAI_API_KEY is required for The Abbot to answer questions.")

    payload = {
        "model": settings.OPENAI_TUTOR_MODEL,
        "instructions": TUTOR_ANSWER_INSTRUCTIONS,
        "input": build_tutor_answer_input(
            concept_id=concept_id,
            concept_name=concept_name,
            concept_summary=concept_summary,
            source_excerpt=source_excerpt,
            chapter_objectives=chapter_objectives,
            literary_metadata=literary_metadata,
            lesson_explanation=lesson_explanation,
            lesson_examples=lesson_examples,
            student_question=student_question,
        ),
        "text": {"format": TUTOR_ANSWER_RESPONSE_SCHEMA},
    }

    api_response = call_openai_responses_api(payload)
    answer = json.loads(extract_output_text(api_response))
    answer["visual_content"] = _normalize_visual_content(answer.get("visual_content"))
    answer["concept_id"] = concept_id
    answer["student_question"] = student_question
    return answer


def _literary_metadata_for_concept(concept) -> dict:
    """Expose literature metadata only for Literary Toolkit concepts."""

    if not is_literary_summary(concept.summary):
        return {}
    return concept.chapter.literary_metadata or {}


def _normalize_lesson(lesson: dict) -> dict:
    if "lesson" in lesson and isinstance(lesson["lesson"], dict):
        lesson = lesson["lesson"]

    lesson["explanation"] = str(
        lesson.get("explanation")
        or lesson.get("lesson_text")
        or lesson.get("teaching")
        or lesson.get("content")
        or ""
    ).strip()

    examples = lesson.get("examples") or []
    if not isinstance(examples, list):
        examples = [str(examples)]

    lesson["examples"] = [str(example) for example in examples[:3] if str(example).strip()]
    if not lesson["examples"]:
        lesson["examples"] = ["Review the explanation above, then try a practice question."]

    if lesson.get("next_action") not in {"ready_for_mcq", "review_explanation"}:
        lesson["next_action"] = "ready_for_mcq" if lesson["explanation"] else "review_explanation"

    lesson["visual_content"] = _normalize_visual_content(lesson.get("visual_content"))

    return lesson


def _normalize_visual_content(visual_content) -> dict | None:
    if not isinstance(visual_content, dict):
        return None

    if _contains_unsafe_visual_text(visual_content):
        return None

    raw_type = str(visual_content.get("type", "")).strip()
    render_mode = str(visual_content.get("render_mode", "")).strip()
    allowed_types = {"graph", "geometry", "chart", "table"}
    if raw_type not in allowed_types:
        return None

    allowed_render_modes_by_type = {
        "graph": {"function_plot"},
        "geometry": {"geometry_diagram"},
        "chart": {"statistics_chart"},
        "table": {"statistics_chart"},
    }
    if render_mode not in allowed_render_modes_by_type[raw_type]:
        return None

    normalized = {
        "type": raw_type,
        "title": str(visual_content.get("title", "")).strip(),
        "description": str(visual_content.get("description", "")).strip(),
        "expression": str(visual_content.get("expression", "")).strip(),
        "render_mode": render_mode,
    }

    if normalized["type"] == "graph":
        if not _is_safe_graph_expression(normalized["expression"]):
            return None
        return normalized

    if normalized["type"] == "geometry" and normalized["render_mode"] == "geometry_diagram":
        allowed_shapes = {
            "circle",
            "triangle",
            "rectangle",
            "square",
            "coordinate_point",
            "line_segment",
            "angle",
            "polygon",
        }
        shape = str(visual_content.get("shape", "")).strip()
        if shape not in allowed_shapes:
            return None

        labels = visual_content.get("labels") or []
        if not isinstance(labels, list):
            labels = []

        annotations = visual_content.get("annotations") or []
        if not isinstance(annotations, list):
            annotations = []

        # Geometry visuals are intentionally structured so the frontend renders
        # known SVG shapes instead of interpreting freeform drawing instructions.
        normalized["shape"] = shape
        normalized["labels"] = [str(label).strip() for label in labels[:8] if str(label).strip()]
        normalized["annotations"] = [
            {
                "label": str(annotation.get("label", "")).strip(),
                "position": str(annotation.get("position", "")).strip(),
            }
            for annotation in annotations[:6]
            if isinstance(annotation, dict) and str(annotation.get("label", "")).strip()
        ]
        return normalized

    if normalized["type"] in {"chart", "table"} and normalized["render_mode"] == "statistics_chart":
        allowed_chart_types = {"bar", "line", "pie", "table"}
        chart_type = str(visual_content.get("chart_type", "")).strip()
        if normalized["type"] == "table" and not chart_type:
            chart_type = "table"
        if chart_type not in allowed_chart_types:
            return None

        raw_data = visual_content.get("data") or []
        if not isinstance(raw_data, list):
            return None

        data = []
        for point in raw_data[:12]:
            if not isinstance(point, dict):
                continue
            label = str(point.get("label", "")).strip()
            try:
                value = float(point.get("value"))
            except (TypeError, ValueError):
                continue
            if label:
                data.append({"label": label, "value": value})

        if not data:
            return None

        # Chart visuals are structured data only. The frontend renders labels as
        # text and never interprets chart data as HTML or executable content.
        normalized["chart_type"] = chart_type
        normalized["x_label"] = str(visual_content.get("x_label", "")).strip()
        normalized["y_label"] = str(visual_content.get("y_label", "")).strip()
        normalized["data"] = data
        return normalized

    return None


def _contains_unsafe_visual_text(value) -> bool:
    """Reject raw markup, executable-looking content, and external resources before rendering."""

    unsafe_patterns = (
        r"<\s*/?\s*[a-zA-Z][^>]*>",
        r"\bjavascript\s*:",
        r"\bdata\s*:",
        r"\bhttps?://",
        r"\bwww\.",
        r"\bon[a-z]+\s*=",
        r"=>",
        r"\bfunction\s*\(",
    )

    if isinstance(value, str):
        return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in unsafe_patterns)
    if isinstance(value, dict):
        return any(_contains_unsafe_visual_text(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_unsafe_visual_text(item) for item in value)
    return False


def _is_safe_graph_expression(expression: str) -> bool:
    """Validate a tiny math-expression subset for plotting; this never evaluates the expression."""

    cleaned = expression.strip()
    if not cleaned:
        return False

    if "=" in cleaned:
        left_side, right_side = cleaned.split("=", 1)
        if left_side.strip().lower() not in {"y", "f(x)"}:
            return False
        cleaned = right_side.strip()

    allowed_functions = {"sin", "cos", "tan", "sqrt", "log", "exp", "abs"}
    allowed_symbols = {"x"}
    tokens = re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?|[()+\-*/^]", cleaned)
    if "".join(tokens).replace(" ", "") != cleaned.replace(" ", ""):
        return False

    for token in re.findall(r"[A-Za-z]+", cleaned):
        if token not in allowed_symbols and token not in allowed_functions:
            return False

    return _has_balanced_parentheses(cleaned)


def _has_balanced_parentheses(value: str) -> bool:
    depth = 0
    for character in value:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
