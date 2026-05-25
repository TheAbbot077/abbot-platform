from django.urls import path

from .views import (
    CurrentConceptMCQSubmissionView,
    CurrentConceptMCQView,
    CurrentUnlockedConceptView,
    DocumentProgressView,
    ProgressDashboardView,
    RestartChapterView,
    RestartCurrentConceptView,
    RestartDocumentView,
    StudentAIAskView,
    StudentAIExaminerCheckView,
    StudentAIMemoryTeachView,
    TutorAskView,
    TutorCurrentConceptView,
)

urlpatterns = [
    path("dashboard/", ProgressDashboardView.as_view(), name="progress-dashboard"),
    path("documents/<int:document_id>/current-concept/", CurrentUnlockedConceptView.as_view(), name="current-concept"),
    path("documents/<int:document_id>/progress/", DocumentProgressView.as_view(), name="document-progress"),
    path("documents/<int:document_id>/tutor/current/", TutorCurrentConceptView.as_view(), name="tutor-current-concept"),
    path("tutor/ask/", TutorAskView.as_view(), name="tutor-ask"),
    path("student-ai/memory/teach/", StudentAIMemoryTeachView.as_view(), name="student-ai-memory-teach"),
    path("student-ai/ask/", StudentAIAskView.as_view(), name="student-ai-ask"),
    path("student-ai/examiner/check/", StudentAIExaminerCheckView.as_view(), name="student-ai-examiner-check"),
    path("documents/<int:document_id>/mcqs/current/", CurrentConceptMCQView.as_view(), name="current-concept-mcqs"),
    path("documents/<int:document_id>/mcqs/current/submit/", CurrentConceptMCQSubmissionView.as_view(), name="submit-current-concept-mcqs"),
    path("documents/<int:document_id>/restart-current-concept/", RestartCurrentConceptView.as_view(), name="restart-current-concept"),
    path("chapters/<int:chapter_id>/restart/", RestartChapterView.as_view(), name="restart-chapter"),
    path("documents/<int:document_id>/restart/", RestartDocumentView.as_view(), name="restart-document"),
]
