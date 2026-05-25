from django.urls import path

from .views import (
    AdminAuditLogListView,
    AdminConceptQualityListView,
    AdminConceptRegenerateMcqsView,
    AdminConceptRegenerateTutorView,
    AdminTextbookDetailView,
    AdminTextbookListView,
    AdminTextbookParserPreviewView,
    AdminTextbookReprocessView,
    AdminUserActivationView,
    AdminUserAnalyticsView,
    AdminUserDetailView,
    AdminUserListView,
    CommandCenterDashboardView,
    HealthCheckView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("admin/command-center/", CommandCenterDashboardView.as_view(), name="command-center-dashboard"),
    path("admin/analytics/users/", AdminUserAnalyticsView.as_view(), name="admin-user-analytics"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:user_id>/<str:action>/", AdminUserActivationView.as_view(), name="admin-user-activation"),
    path("admin/textbooks/", AdminTextbookListView.as_view(), name="admin-textbook-list"),
    path("admin/textbooks/<int:document_id>/", AdminTextbookDetailView.as_view(), name="admin-textbook-detail"),
    path("admin/textbooks/<int:document_id>/parser-preview/", AdminTextbookParserPreviewView.as_view(), name="admin-textbook-parser-preview"),
    path("admin/textbooks/<int:document_id>/reprocess/", AdminTextbookReprocessView.as_view(), name="admin-textbook-reprocess"),
    path("admin/quality/concepts/", AdminConceptQualityListView.as_view(), name="admin-concept-quality-list"),
    path("admin/quality/concepts/<int:concept_id>/regenerate-mcqs/", AdminConceptRegenerateMcqsView.as_view(), name="admin-concept-regenerate-mcqs"),
    path("admin/quality/concepts/<int:concept_id>/regenerate-tutor/", AdminConceptRegenerateTutorView.as_view(), name="admin-concept-regenerate-tutor"),
    path("admin/audit-logs/", AdminAuditLogListView.as_view(), name="admin-audit-log-list"),
]
