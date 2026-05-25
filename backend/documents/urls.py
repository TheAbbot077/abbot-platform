from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChapterConceptListView, DocumentViewSet, SubjectViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="subject")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("chapters/<int:chapter_id>/concepts/", ChapterConceptListView.as_view(), name="chapter-concept-list"),
    path("", include(router.urls)),
]
