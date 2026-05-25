from django.contrib import admin

from .models import (
    ChapterProgress,
    ConceptLesson,
    ConceptMastery,
    ConceptProgress,
    QuizAttempt,
    QuizQuestion,
    ReinforcementRecommendation,
    StudentAIReinforcementReport,
    StudentAIMemory,
    StudentAISpotQuizAttempt,
    TutorMessage,
)

admin.site.register(ChapterProgress)
admin.site.register(ConceptProgress)
admin.site.register(ConceptMastery)
admin.site.register(ConceptLesson)
admin.site.register(QuizQuestion)
admin.site.register(QuizAttempt)
admin.site.register(TutorMessage)
admin.site.register(StudentAIMemory)
admin.site.register(StudentAISpotQuizAttempt)
admin.site.register(StudentAIReinforcementReport)
admin.site.register(ReinforcementRecommendation)
