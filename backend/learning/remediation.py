from .models import QuizQuestion


def build_remediation_guidance(missed_questions: list[QuizQuestion]) -> str:
    if not missed_questions:
        return ""

    guidance_lines = [
        "Review this concept before trying again.",
        "Focus on the points below:",
    ]
    for question in missed_questions:
        guidance_lines.append(f"- {question.explanation}")

    return "\n".join(guidance_lines)
