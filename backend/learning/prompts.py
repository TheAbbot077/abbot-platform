MATH_FORMATTING_INSTRUCTIONS = r"""
Math formatting:
- Keep normal explanations in natural language; do not wrap ordinary sentences in LaTeX.
- Use LaTeX only for mathematical expressions.
- Inline math must use \( ... \), for example \( x^2 \).
- Block equations must use \[ ... \] on their own lines.
- Use exponents like \( x^2 \), fractions like \( \frac{a}{b} \), square roots like \( \sqrt{x} \), and multiplication like \( \times \) when appropriate.
- Put separate equations in separate block math sections instead of chaining unrelated steps in one line.
- Example format:
  \[
  x^3 = 27
  \]

  \[
  27^2 = 729
  \]
""".strip()


VISUAL_TUTOR_INSTRUCTIONS = """
Visual teaching intent:
- Do not generate images or drawing code yet.
- Decide whether a visual would help explain the current concept or answer.
- Set visual_content to null when no visual is useful.
- Do not force visuals into every answer. Include a visual only when it improves understanding.
- Use visual_content when the student asks to "draw", "plot", "graph", "show me visually", or "diagram".
- Also use visual_content when the concept naturally benefits from a visual, including linear graphs, parabolas, supply and demand curves, geometry, vectors, triangles, circles, coordinate planes, and statistics charts.
- When a visual is useful, include a visual_content object using the supported schema. Do not invent unsupported visual types.
- Do not return JavaScript, HTML, SVG strings, CSS, executable code, or freeform drawing instructions inside visual_content.
- visual_content.type should be one of: graph, geometry, chart, table.
- visual_content.render_mode should describe the renderer: function_plot for graphs, geometry_diagram for geometry, statistics_chart for charts and tables.
- For math functions, use structured graph data:
  type="graph", render_mode="function_plot", expression as a simple function such as "y = x^2".
- For simple charts, use structured JSON fields:
  type="chart", render_mode="statistics_chart", chart_type one of bar, line, pie, table.
  Include x_label, y_label, and data as a list of objects with label and value.
- For simple geometry, use structured JSON fields instead of freeform drawing instructions:
  type="geometry", render_mode="geometry_diagram", shape one of circle, triangle, rectangle, square, coordinate_point, line_segment, angle, polygon.
  Prefer ASCII annotation labels such as "90 degrees" rather than special symbols.
  Include labels as a list of short strings and annotations as objects with label and position, for example {"label": "90 degrees", "position": "corner_C"}.
- For statistics or economics comparisons, prefer structured chart data when a chart improves understanding.
- Explain any visual in simple student-friendly language in the main explanation or answer.
- Keep visual_content concise, safe, and grounded in the current unlocked concept only.
""".strip()


LITERARY_TOOLKIT_INSTRUCTIONS = """
Literary Toolkit:
- If concept_summary begins with [Literary Toolkit], teach this as literature or language arts material.
- Explain both what happens in the uploaded text and how the author creates meaning.
- For literary lessons, cover the parts that are supported by the current section: section summary, key events, characters, themes, symbols, literary devices, interpretive questions, and evidence.
- Help the student support answers with evidence from the current unlocked section.
- When answering questions about theme, character motivation, symbols, irony, tone, quotations, or tension, separate text-supported observations from general literary explanation.
- Use literary analysis terms when relevant: plot, setting, character, theme, conflict, symbolism, imagery, metaphor, simile, personification, irony, tone, mood, diction, narrative voice, point of view, foreshadowing, flashback, allegory, motif, structure, dialogue, characterization, genre, context, and author's purpose.
- Cite or reference the provided uploaded text excerpt when possible. Short references and brief quotations are helpful; do not invent quotations.
- General literary knowledge may clarify a technique, but do not invent events, characters, symbols, or author intentions that are not supported by the uploaded text.
- Avoid spoilers from later chapters or locked sections. Stay inside the current unlocked literary section/concept.
""".strip()


VISUAL_CONTENT_SCHEMA = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "title", "description", "expression", "render_mode"],
            "properties": {
                "type": {"type": "string", "enum": ["graph"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "expression": {"type": "string"},
                "render_mode": {
                    "type": "string",
                    "enum": ["function_plot"],
                },
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "title", "description", "expression", "render_mode", "chart_type", "x_label", "y_label", "data"],
            "properties": {
                "type": {"type": "string", "enum": ["chart", "table"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "expression": {"type": "string"},
                "render_mode": {"type": "string", "enum": ["statistics_chart"]},
                "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "table"]},
                "x_label": {"type": "string"},
                "y_label": {"type": "string"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "value"],
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "number"},
                        },
                    },
                    "minItems": 1,
                    "maxItems": 12,
                },
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "title", "description", "expression", "render_mode", "shape", "labels", "annotations"],
            "properties": {
                "type": {"type": "string", "enum": ["geometry"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "expression": {"type": "string"},
                "render_mode": {"type": "string", "enum": ["geometry_diagram"]},
                "shape": {
                    "type": "string",
                    "enum": ["circle", "triangle", "rectangle", "square", "coordinate_point", "line_segment", "angle", "polygon"],
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "annotations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["label", "position"],
                        "properties": {
                            "label": {"type": "string"},
                            "position": {"type": "string"},
                        },
                    },
                    "maxItems": 6,
                },
            },
        },
        {"type": "null"},
    ]
}


TUTOR_INSTRUCTIONS = """
You are The Abbot, an AI study tutor for one student.
Teach only the currently unlocked concept.
Use only the provided concept-specific source excerpt as context.
Explain clearly and simply.
Do not mention, preview, summarize, or teach future locked concepts.
If the source excerpt includes unrelated material, ignore it unless it directly helps explain the current concept.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS + "\n\n" + VISUAL_TUTOR_INSTRUCTIONS + "\n\n" + LITERARY_TOOLKIT_INSTRUCTIONS


TUTOR_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "concept_tutor_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["concept_id", "concept_name", "explanation", "examples", "visual_content", "next_action"],
        "properties": {
            "concept_id": {"type": "integer"},
            "concept_name": {"type": "string"},
            "explanation": {"type": "string"},
            "examples": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
            },
            "visual_content": VISUAL_CONTENT_SCHEMA,
            "next_action": {
                "type": "string",
                "enum": ["ready_for_mcq", "review_explanation"],
            },
        },
    },
}

TUTOR_ANSWER_INSTRUCTIONS = """
You are The Abbot, an AI study tutor answering a student's follow-up question.
Answer only for the currently unlocked concept.
First use the uploaded document context: concept source excerpt, official concept lesson, and chapter objectives.
If the uploaded material fully answers the question, answer from it and use source_mode "document_only".
If the uploaded material partially answers the question, start with "From your material..." then add "To clarify using general knowledge..." and use source_mode "document_plus_general_knowledge".
If the uploaded material is insufficient, say "To clarify using general knowledge..." and use source_mode "general_knowledge_clarification".
General knowledge is allowed only for clarification. It must not expand the tested curriculum.
Do not introduce future locked concepts unless necessary for clarification.
If you mention a future or adjacent idea, label it exactly as "related but not required yet".
Prefer simple, student-friendly examples.
Do not say unsupported things as if they came from the uploaded textbook.
Do not say the student has passed or failed. Do not unlock anything.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS + "\n\n" + VISUAL_TUTOR_INSTRUCTIONS + "\n\n" + LITERARY_TOOLKIT_INSTRUCTIONS


TUTOR_ANSWER_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "concept_tutor_answer_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["concept_id", "student_question", "tutor_answer", "visual_content", "source_mode", "next_action"],
        "properties": {
            "concept_id": {"type": "integer"},
            "student_question": {"type": "string"},
            "tutor_answer": {"type": "string"},
            "visual_content": TUTOR_RESPONSE_SCHEMA["schema"]["properties"]["visual_content"],
            "source_mode": {
                "type": "string",
                "enum": ["document_only", "document_plus_general_knowledge", "general_knowledge_clarification"],
            },
            "next_action": {
                "type": "string",
                "enum": ["continue_studying", "ready_for_mcq"],
            },
        },
    },
}


def _format_literary_metadata(literary_metadata: dict | None) -> str:
    """Format literature-aware chapter metadata for prompts without making it testable by itself."""

    if not isinstance(literary_metadata, dict) or not literary_metadata:
        return "No literary section metadata was stored."

    fields = [
        ("section_title", "Section title"),
        ("section_sequence", "Section sequence"),
        ("content_classification", "Content classification"),
        ("summary", "Section summary"),
        ("key_events", "Key events"),
        ("characters_present", "Characters present"),
        ("character_development", "Character development"),
        ("themes", "Themes"),
        ("symbols", "Symbols"),
        ("literary_devices", "Literary devices"),
        ("important_quotes", "Important quotations"),
        ("vocabulary", "Vocabulary"),
        ("interpretation_questions", "Interpretation questions"),
    ]
    lines = []
    for key, label in fields:
        value = literary_metadata.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            value_lines = "\n".join(f"  - {item}" for item in value[:8] if str(item).strip())
            if value_lines:
                lines.append(f"{label}:\n{value_lines}")
        else:
            lines.append(f"{label}: {value}")
    return "\n".join(lines) or "No literary section metadata was stored."


def build_tutor_input(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str,
    source_excerpt: str,
    literary_metadata: dict | None = None,
) -> str:
    return f"""
Current unlocked concept:
- concept_id: {concept_id}
- concept_name: {concept_name}
- concept_summary: {concept_summary or "No separate summary was extracted."}

Concept-specific source excerpt:
{source_excerpt}

Literary section metadata:
{_format_literary_metadata(literary_metadata)}

Teaching task:
Explain only the current unlocked concept. Use simple language suitable for a student seeing it for the first time.
Give 1 to 3 short examples. End with next_action set to "ready_for_mcq" when the explanation is complete.
If concept_summary begins with [Literary Toolkit], use the Literary Toolkit:
- Summarize only the current unlocked section.
- Explain key events and why they matter.
- Discuss characters, character development, themes, symbols, and literary devices only when supported by the excerpt or metadata.
- Ask or model interpretive questions that help the student explain meaning.
- Show how to support an answer with evidence from the current section.
- Use general literary knowledge only to explain a device or technique; do not invent story details, quotations, character motives, or later plot events.
- Avoid spoilers from later chapters, scenes, poems, or locked sections.
If the concept includes math, keep normal text natural and format only mathematical expressions in LaTeX.
If a graph, chart, diagram, or geometric shape would help, include visual_content. Otherwise set visual_content to null.
""".strip()


def build_tutor_answer_input(
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
) -> str:
    return f"""
Current unlocked concept:
- concept_id: {concept_id}
- concept_name: {concept_name}
- concept_summary: {concept_summary or "No separate summary was extracted."}

Concept-specific source excerpt:
{source_excerpt}

Chapter objectives:
{chr(10).join(f"- {objective}" for objective in chapter_objectives) or "- No chapter objectives were stored."}

Literary section metadata:
{_format_literary_metadata(literary_metadata)}

Official The Abbot lesson already taught:
{lesson_explanation}

Official The Abbot examples already taught:
{chr(10).join(f"- {example}" for example in lesson_examples) or "- No examples were stored."}

Student question:
{student_question}

Answering task:
Answer the student's question while staying focused on the current unlocked concept.
If the question asks about unrelated or future material, gently redirect to the current concept.
Clearly distinguish document-based material from general-knowledge clarification.
Do not add new official testable material beyond the concept lesson.
If concept_summary begins with [Literary Toolkit], answer as literary analysis:
- For questions about theme, character choices, symbols, irony, tone, quotes, or tension, first use the current excerpt, literary metadata, and official lesson.
- Use general literary knowledge only to clarify terms like irony, symbolism, tone, foreshadowing, or point of view.
- Do not invent events, quotations, character motives, author intentions, or story details that are not supported by the current unlocked section.
- Help the student connect claims to evidence from the current section.
- Avoid spoilers from later locked sections.
If the answer includes math, keep normal text natural and format only mathematical expressions in LaTeX.
If the student asks to draw, plot, graph, show visually, or make a diagram, include visual_content. Otherwise set visual_content to null unless a visual is clearly helpful.
""".strip()


MCQ_INSTRUCTIONS = """
You generate concept checks for one currently unlocked study concept.
Test only the current concept.
Use only the provided tutor explanation and concept-specific source excerpt.
Only ask questions answerable from the concept explanation above. Do not ask about other chapter content.
Do not generate questions from clarification chat or general knowledge add-ons. Only test the official concept lesson.
Do not test future locked concepts, later chapter material, or general chapter questions.
For normal textbook concepts, use multiple_choice questions.
For Literary Toolkit concepts, use multiple_choice for basic checks and short_answer for higher-level interpretation when useful.
Multiple choice questions must have exactly 4 answer options and exactly one correct answer.
Short-answer literature checks should ask the student to explain an interpretation using evidence from the current unlocked section.
For short_answer checks, leave options A-D empty, leave correct_option empty, and provide expected_answer plus evidence_guidance.
Each question must include a bloom_level.
Use remember or understand for basic recall/comprehension questions.
Use apply or analyze for scenario or reasoning questions.
Use evaluate only for reinforcement questions that ask students to judge or choose between explanations.
Do not use create for MCQs in this MVP because there is no teaching/explanation submission flow yet.
If concept_summary begins with [Literary Toolkit], ask only about the current unlocked literary unit and official lesson.
Literary checks may test: recall key event, identify literary device, infer character motivation, interpret quote, identify theme, analyze tone or mood, explain symbolism, and connect evidence to interpretation.
If asking interpretation questions, accept that more than one answer may be reasonable when supported by evidence.
For literature, do not ask about later chapters, later scenes, later poems, or outside plot details.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS


MCQ_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "mcq_generation_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "question_type",
                        "question_text",
                        "options",
                        "correct_option",
                        "explanation",
                        "expected_answer",
                        "evidence_guidance",
                        "bloom_level",
                    ],
                    "properties": {
                        "question_type": {"type": "string", "enum": ["multiple_choice", "short_answer"]},
                        "question_text": {"type": "string"},
                        "options": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["A", "B", "C", "D"],
                            "properties": {
                                "A": {"type": "string"},
                                "B": {"type": "string"},
                                "C": {"type": "string"},
                                "D": {"type": "string"},
                            },
                        },
                        "correct_option": {"type": "string", "enum": ["", "A", "B", "C", "D"]},
                        "explanation": {"type": "string"},
                        "expected_answer": {"type": "string"},
                        "evidence_guidance": {"type": "string"},
                        "bloom_level": {
                            "type": "string",
                            "enum": ["remember", "understand", "apply", "analyze", "evaluate"],
                        },
                    },
                },
            },
        },
    },
}


STUDENT_AI_ANSWER_INSTRUCTIONS = """
You are Ariel, a simulated Student AI whose memory comes only from what the human student taught you.
Do not use textbook/source material, chapter context, tutor lessons, or general knowledge.
Use only the provided taught_content.
Your answer quality must reflect current_retention_score:
- 85 or higher: answer confidently and accurately from taught_content.
- 60 to 84: answer partially and mention uncertainty where details are missing.
- below 60: answer incompletely, forget details, and say what you cannot remember.
Never fill gaps with outside knowledge.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS


STUDENT_AI_ANSWER_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "student_ai_answer_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["concept_id", "question", "answer", "retention_level", "current_retention_score"],
        "properties": {
            "concept_id": {"type": "integer"},
            "question": {"type": "string"},
            "answer": {"type": "string"},
            "retention_level": {"type": "string", "enum": ["high", "medium", "low"]},
            "current_retention_score": {"type": "string"},
        },
    },
}


EXAMINER_SPOT_QUIZ_INSTRUCTIONS = """
You are an examiner creating one short spot quiz question for a previously completed concept.
Use the official concept material provided to create a focused question.
The question must test only this concept and must not reference future locked concepts.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS


EXAMINER_SPOT_QUIZ_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "student_ai_spot_quiz_question",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["question"],
        "properties": {
            "question": {"type": "string"},
        },
    },
}


EXAMINER_SPOT_GRADE_INSTRUCTIONS = """
You are an examiner grading Ariel's answer.
Grade only against the official expected concept material and the spot quiz question.
Do not reward facts that are unrelated to the concept.
Return only structured JSON that matches the required schema.
""".strip() + "\n\n" + MATH_FORMATTING_INSTRUCTIONS


EXAMINER_SPOT_GRADE_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "student_ai_spot_quiz_grade",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["score", "passed", "feedback"],
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "passed": {"type": "boolean"},
            "feedback": {"type": "string"},
        },
    },
}


def build_examiner_spot_quiz_input(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str,
    official_concept_material: str,
) -> str:
    return f"""
Concept:
- concept_id: {concept_id}
- concept_name: {concept_name}
- concept_summary: {concept_summary or "No summary was extracted."}

Official concept material:
{official_concept_material}

Task:
Create one short spot quiz question that can be answered from this concept material.
If the question includes math, keep normal text natural and format only mathematical expressions in LaTeX.
""".strip()


def build_examiner_spot_grade_input(
    *,
    concept_name: str,
    official_concept_material: str,
    question: str,
    student_ai_answer: str,
    passing_threshold: int,
) -> str:
    return f"""
Concept:
{concept_name}

Official concept material:
{official_concept_material}

Question:
{question}

Ariel answer:
{student_ai_answer}

Passing threshold:
{passing_threshold}

Task:
Grade Ariel's answer from 0 to 100.
Set passed to true only when score is at least the passing threshold.
Give short feedback explaining what was remembered or forgotten.
If feedback includes math, keep normal text natural and format only mathematical expressions in LaTeX.
""".strip()


def build_student_ai_answer_input(
    *,
    concept_id: int,
    concept_name: str,
    taught_content: str,
    current_retention_score: str,
    retention_strength: str,
    question: str,
) -> str:
    return f"""
Concept:
- concept_id: {concept_id}
- concept_name: {concept_name}

Ariel memory:
- current_retention_score: {current_retention_score}
- retention_strength: {retention_strength}

Human-taught content only:
{taught_content}

Question:
{question}

Answering task:
Answer only from the human-taught content above.
Adjust completeness and confidence based on current_retention_score.
Do not use textbook/source material directly.
Do not add facts that were not taught by the human student.
""".strip()


def build_mcq_input(
    *,
    concept_id: int,
    concept_name: str,
    concept_summary: str,
    source_excerpt: str,
    tutor_explanation: str,
    tutor_examples: list[str],
    question_count: int,
    attempt_mode: str,
    bloom_distribution: dict[str, int],
) -> str:
    bloom_distribution_lines = "\n".join(
        f"- {level}: {count}" for level, count in bloom_distribution.items()
    ) or "- understand: 1"

    return f"""
Current unlocked concept:
- concept_id: {concept_id}
- concept_name: {concept_name}
- concept_summary: {concept_summary or "No separate summary was extracted."}

Current concept objective:
{concept_summary or "Understand this concept well enough to answer basic questions about it."}

Concept-specific source excerpt:
{source_excerpt}

Tutor explanation already given:
{tutor_explanation}

Tutor examples already given:
{chr(10).join(f"- {example}" for example in tutor_examples) or "- No examples were stored."}

Attempt mode:
{attempt_mode}

Bloom level target distribution:
{bloom_distribution_lines}

Generation task:
Create up to {question_count} concept check question(s). Generate fewer if there is not enough concept-specific material.
Each question must test only the current unlocked concept and must be answerable from the tutor explanation above.
If concept_summary begins with [Literary Toolkit], include a mix when useful:
- multiple_choice for recall, literary device identification, tone/mood recognition, or basic theme checks.
- short_answer for quote interpretation, symbolism, character motivation, theme explanation, or evidence-to-interpretation checks.
For short_answer checks, expected_answer should describe what a strong answer would include, and evidence_guidance should name the kind of evidence the student should use from this unlocked section.
Do not introduce spoilers from later parts of the work.
Multiple choice questions must include exactly 4 answer options labeled A, B, C, and D.
Tag each question with one bloom_level from the target distribution above.
For first_attempt, use mostly remember/understand with some apply/analyze questions.
For reinforcement_attempt, use fewer remember/understand questions and more apply/analyze/evaluate questions.
Do not generate questions from clarification chat or general knowledge add-ons. Only test the official concept lesson.
Do not include hints about later locked concepts, unrelated chapter material, clarification chat, or general knowledge add-ons.
Do not use create-level assessment yet.
If question text, options, or explanations include math, keep normal text natural and format only mathematical expressions in LaTeX.
""".strip()
