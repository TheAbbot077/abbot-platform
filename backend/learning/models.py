from django.conf import settings
from django.db import models

from documents.models import Chapter, Concept


class ProgressStatus(models.TextChoices):
    LOCKED = "locked", "Locked"
    UNLOCKED = "unlocked", "Unlocked"
    IN_PROGRESS = "in_progress", "In progress"
    MASTERED = "mastered", "Mastered"


class BloomLevel(models.TextChoices):
    REMEMBER = "remember", "Remember"
    UNDERSTAND = "understand", "Understand"
    APPLY = "apply", "Apply"
    ANALYZE = "analyze", "Analyze"
    EVALUATE = "evaluate", "Evaluate"
    CREATE = "create", "Create"


class MasteryStrength(models.TextChoices):
    FAST = "fast", "Fast"
    MEDIUM = "medium", "Medium"
    SLOW = "slow", "Slow"


class RecommendationPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class QuizQuestionType(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
    SHORT_ANSWER = "short_answer", "Short answer"


class ChapterProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chapter_progress")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="student_progress")
    status = models.CharField(max_length=32, choices=ProgressStatus.choices, default=ProgressStatus.LOCKED)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    mastered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "chapter"], name="unique_chapter_progress_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.chapter} - {self.status}"


class ConceptProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="concept_progress")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="student_progress")
    status = models.CharField(max_length=32, choices=ProgressStatus.choices, default=ProgressStatus.LOCKED)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    mastered_at = models.DateTimeField(null=True, blank=True)
    attempts_count = models.PositiveIntegerField(default=0)
    last_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_concept_progress_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.concept} - {self.status}"


class QuizQuestion(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="quiz_questions")
    question_type = models.CharField(
        max_length=32,
        choices=QuizQuestionType.choices,
        default=QuizQuestionType.MULTIPLE_CHOICE,
    )
    bloom_level = models.CharField(max_length=32, choices=BloomLevel.choices, default=BloomLevel.UNDERSTAND)
    question_text = models.TextField()
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_option = models.CharField(
        max_length=1,
        choices=[
            ("A", "A"),
            ("B", "B"),
            ("C", "C"),
            ("D", "D"),
        ],
        blank=True,
    )
    explanation = models.TextField()
    expected_answer = models.TextField(blank=True)
    evidence_guidance = models.TextField(blank=True)
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.concept}: {self.question_text[:80]}"


class ConceptLesson(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="concept_lessons")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="lessons")
    source_excerpt = models.TextField()
    explanation = models.TextField()
    examples = models.JSONField(default=list, blank=True)
    visual_content = models.JSONField(default=dict, blank=True)
    next_action = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_concept_lesson_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.concept}"


class TutorMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_messages")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="tutor_messages")
    student_question = models.TextField()
    tutor_answer = models.TextField()
    visual_content = models.JSONField(default=dict, blank=True)
    source_mode = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.concept}: {self.student_question[:60]}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="quiz_attempts")
    submitted_answers = models.JSONField()
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    score = models.DecimalField(max_digits=5, decimal_places=2)
    bloom_level_scores = models.JSONField(default=dict, blank=True)
    passed = models.BooleanField()
    remediation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.concept} - {self.score}%"


class ConceptMastery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="concept_mastery")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="mastery")
    bloom_level_scores = models.JSONField(default=dict, blank=True)
    mastery_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mastery_strength = models.CharField(max_length=32, choices=MasteryStrength.choices, default=MasteryStrength.FAST)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    next_review_at = models.DateTimeField(null=True, blank=True)
    forgetting_rate = models.DecimalField(max_digits=8, decimal_places=5, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_concept_mastery_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.concept} mastery"


class StudentAIMemory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_ai_memories")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="student_ai_memories")
    taught_content = models.TextField()
    taught_at = models.DateTimeField()
    initial_mastery_score = models.DecimalField(max_digits=5, decimal_places=2)
    current_retention_score = models.DecimalField(max_digits=5, decimal_places=2)
    retention_strength = models.CharField(max_length=32, choices=MasteryStrength.choices, default=MasteryStrength.FAST)
    last_spot_quiz_at = models.DateTimeField(null=True, blank=True)
    next_review_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_student_ai_memory_per_user_concept"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - Student AI memory - {self.concept}"


class StudentAISpotQuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_ai_spot_quizzes")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="student_ai_spot_quizzes")
    memory = models.ForeignKey(StudentAIMemory, on_delete=models.CASCADE, related_name="spot_quiz_attempts")
    question = models.TextField()
    student_ai_answer = models.TextField()
    score = models.DecimalField(max_digits=5, decimal_places=2)
    passed = models.BooleanField()
    feedback = models.TextField(blank=True)
    retention_score_at_quiz = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} - Student AI spot quiz - {self.concept} - {self.score}%"


class StudentAIReinforcementReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_ai_reports")
    report_date = models.DateField()
    recommendations = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "report_date"], name="unique_student_ai_report_per_user_day"),
        ]
        ordering = ["-report_date"]

    def __str__(self) -> str:
        return f"{self.user} - reinforcement report - {self.report_date}"


class ReinforcementRecommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reinforcement_recommendations")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="reinforcement_recommendations")
    reason = models.TextField()
    failed_bloom_level = models.CharField(max_length=32, choices=BloomLevel.choices, default=BloomLevel.UNDERSTAND)
    student_ai_score = models.DecimalField(max_digits=5, decimal_places=2)
    recommended_action = models.CharField(max_length=255)
    friendly_label = models.CharField(max_length=120, default="Memory refresher")
    friendly_message = models.TextField(blank=True)
    mission_title = models.CharField(max_length=160, default="Daily rescue mission")
    priority = models.CharField(max_length=32, choices=RecommendationPriority.choices, default=RecommendationPriority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} - reinforce {self.concept} - {self.priority}"
