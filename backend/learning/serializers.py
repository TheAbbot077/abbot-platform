from rest_framework import serializers

from .models import (
    ChapterProgress,
    ConceptProgress,
    ProgressStatus,
    QuizAttempt,
    QuizQuestion,
    QuizQuestionType,
    StudentAIMemory,
    StudentAISpotQuizAttempt,
)


class ConceptProgressSerializer(serializers.ModelSerializer):
    concept_id = serializers.IntegerField(source="concept.id")
    title = serializers.CharField(source="concept.title")
    chapter_id = serializers.IntegerField(source="concept.chapter_id")
    chapter_sequence_number = serializers.IntegerField(source="concept.chapter.sequence_number")
    sequence_number = serializers.IntegerField(source="concept.sequence_number")
    is_required = serializers.BooleanField(source="concept.is_required")
    subject_id = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    def get_subject_id(self, concept_progress: ConceptProgress):
        return concept_progress.concept.chapter.document.subject_id

    def get_subject_name(self, concept_progress: ConceptProgress):
        subject = concept_progress.concept.chapter.document.subject
        return subject.name if subject else None

    class Meta:
        model = ConceptProgress
        fields = [
            "concept_id",
            "chapter_id",
            "subject_id",
            "subject_name",
            "chapter_sequence_number",
            "title",
            "sequence_number",
            "is_required",
            "status",
            "attempts_count",
            "last_score",
            "unlocked_at",
            "mastered_at",
        ]


class ChapterProgressSerializer(serializers.ModelSerializer):
    chapter_id = serializers.IntegerField(source="chapter.id")
    title = serializers.CharField(source="chapter.title")
    sequence_number = serializers.IntegerField(source="chapter.sequence_number")
    concepts = serializers.SerializerMethodField()

    class Meta:
        model = ChapterProgress
        fields = [
            "chapter_id",
            "title",
            "sequence_number",
            "status",
            "unlocked_at",
            "mastered_at",
            "concepts",
        ]

    def get_concepts(self, chapter_progress: ChapterProgress):
        user = self.context["request"].user
        progress_rows = (
            ConceptProgress.objects.filter(user=user, concept__chapter=chapter_progress.chapter)
            .select_related("concept", "concept__chapter")
            .order_by("concept__sequence_number")
        )
        return ConceptProgressSerializer(progress_rows, many=True).data


class TutorLessonSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    concept_name = serializers.CharField()
    explanation = serializers.CharField()
    examples = serializers.ListField(child=serializers.CharField(), min_length=1, max_length=3)
    visual_content = serializers.JSONField(required=False, allow_null=True)
    is_literary = serializers.BooleanField(required=False)
    literary_metadata = serializers.JSONField(required=False)
    next_action = serializers.ChoiceField(choices=["ready_for_mcq", "review_explanation"])


class TutorQuestionSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.CharField(trim_whitespace=True, max_length=2000)


class TutorAnswerSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    student_question = serializers.CharField()
    tutor_answer = serializers.CharField()
    visual_content = serializers.JSONField(required=False, allow_null=True)
    source_mode = serializers.ChoiceField(
        choices=["document_only", "document_plus_general_knowledge", "general_knowledge_clarification"]
    )
    next_action = serializers.ChoiceField(choices=["continue_studying", "ready_for_mcq"])


class StudentAITeachSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    taught_content = serializers.CharField(trim_whitespace=True, max_length=10000)
    initial_mastery_score = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)


class StudentAIMemorySerializer(serializers.ModelSerializer):
    concept_id = serializers.IntegerField(source="concept.id")

    class Meta:
        model = StudentAIMemory
        fields = [
            "concept_id",
            "taught_content",
            "taught_at",
            "initial_mastery_score",
            "current_retention_score",
            "retention_strength",
            "last_spot_quiz_at",
            "next_review_at",
        ]


class StudentAIQuestionSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.CharField(trim_whitespace=True, max_length=2000)


class StudentAIAnswerSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    question = serializers.CharField()
    answer = serializers.CharField()
    retention_level = serializers.ChoiceField(choices=["high", "medium", "low"])
    current_retention_score = serializers.CharField()


class StudentAIExaminerCheckSerializer(serializers.Serializer):
    concept_id = serializers.IntegerField()
    subject_id = serializers.IntegerField(required=False, allow_null=True)


class StudentAIExaminerResultSerializer(serializers.ModelSerializer):
    attempt_id = serializers.IntegerField(source="id")
    concept_id = serializers.IntegerField(source="concept.id")
    celebration = serializers.SerializerMethodField()

    class Meta:
        model = StudentAISpotQuizAttempt
        fields = [
            "attempt_id",
            "concept_id",
            "question",
            "student_ai_answer",
            "score",
            "passed",
            "feedback",
            "retention_score_at_quiz",
            "celebration",
        ]

    def get_celebration(self, attempt: StudentAISpotQuizAttempt) -> str | None:
        return "ariel_examiner_passed" if attempt.passed else None


class QuizQuestionSerializer(serializers.ModelSerializer):
    concept_id = serializers.IntegerField(source="concept.id")
    options = serializers.SerializerMethodField()

    class Meta:
        model = QuizQuestion
        fields = [
            "id",
            "concept_id",
            "question_type",
            "question_text",
            "options",
            "evidence_guidance",
            "is_answered",
            "bloom_level",
        ]

    def get_options(self, question: QuizQuestion):
        if question.question_type == QuizQuestionType.SHORT_ANSWER:
            return {}
        return {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        }


class QuizAnswerSubmissionSerializer(serializers.Serializer):
    answers = serializers.DictField(child=serializers.CharField(trim_whitespace=True, max_length=4000), allow_empty=False)


class QuizAttemptResultSerializer(serializers.ModelSerializer):
    attempt_id = serializers.IntegerField(source="id")
    concept_id = serializers.IntegerField(source="concept.id")
    next_action = serializers.SerializerMethodField()
    celebration = serializers.SerializerMethodField()
    remediation_message = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = [
            "attempt_id",
            "concept_id",
            "score",
            "bloom_level_scores",
            "passed",
            "total_questions",
            "correct_answers",
            "remediation",
            "remediation_message",
            "available_actions",
            "next_action",
            "celebration",
        ]

    def get_next_action(self, attempt: QuizAttempt) -> str:
        return "next_concept_unlocked" if attempt.passed else "review_remediation"

    def get_remediation_message(self, attempt: QuizAttempt) -> str:
        if attempt.passed:
            return ""
        return "You did not pass this check yet. Choose how you want to continue."

    def get_available_actions(self, attempt: QuizAttempt) -> list[str]:
        if attempt.passed:
            return []
        return ["ask_tutor", "restart_concept", "retry_quiz"]

    def get_celebration(self, attempt: QuizAttempt) -> str | None:
        if not attempt.passed:
            return None

        chapter_progress = ChapterProgress.objects.filter(user=attempt.user, chapter=attempt.concept.chapter).first()
        if chapter_progress and chapter_progress.status == ProgressStatus.MASTERED:
            document_has_unmastered_chapters = ChapterProgress.objects.filter(
                user=attempt.user,
                chapter__document=attempt.concept.chapter.document,
            ).exclude(status=ProgressStatus.MASTERED).exists()
            return "chapter_completed" if document_has_unmastered_chapters else "document_completed"

        return "concept_passed"


class DashboardSerializer(serializers.Serializer):
    documents = serializers.ListField(child=serializers.DictField())
    student_ai_reinforcement = serializers.DictField(required=False)
    teachback_memory_engine = serializers.DictField(required=False)
