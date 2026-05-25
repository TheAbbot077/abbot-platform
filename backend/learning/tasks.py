from celery import shared_task

from .spot_quiz import run_due_student_ai_spot_quizzes


@shared_task
def run_student_ai_spot_quizzes() -> int:
    """Automatically detect weak Student AI memories and group recommendations."""

    return run_due_student_ai_spot_quizzes()
