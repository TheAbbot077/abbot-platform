from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserProfile, UserRole
from core.models import AdminAuditLog
from documents.models import Chapter, Concept, Document, DocumentStatus, Subject
from learning.models import ConceptLesson, ConceptProgress, ProgressStatus, QuizAttempt, QuizQuestion


class CommandCenterDashboardApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.student = get_user_model().objects.create_user(
            username="student",
            email="student@example.com",
            password="password123",
        )
        self.staff = get_user_model().objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password123",
            is_staff=True,
        )
        self.user_admin = get_user_model().objects.create_user(
            username="user-admin",
            email="admin@example.com",
            password="password123",
            is_staff=True,
        )
        self.user_admin.user_permissions.add(
            Permission.objects.get(codename="change_user", content_type__app_label="accounts")
        )
        self.user_admin.user_permissions.add(
            Permission.objects.get(codename="view_adminauditlog", content_type__app_label="core")
        )
        self.textbook_admin = get_user_model().objects.create_user(
            username="textbook-admin",
            email="textbook-admin@example.com",
            password="password123",
            is_staff=True,
        )
        self.textbook_admin.user_permissions.add(
            Permission.objects.get(codename="change_document", content_type__app_label="documents")
        )
        self.quality_admin = get_user_model().objects.create_user(
            username="quality-admin",
            email="quality-admin@example.com",
            password="password123",
            is_staff=True,
        )
        self.quality_admin.user_permissions.add(
            Permission.objects.get(codename="change_quizquestion", content_type__app_label="learning")
        )

        self.subject = Subject.objects.create(owner=self.student, name="Economics")
        UserProfile.objects.create(
            user=self.student,
            country="Lesotho",
            role=UserRole.STUDENT,
            age_range="16_18",
            gender="prefer_not_to_say",
            education_level="high_school",
            login_count=2,
        )
        self.document = Document.objects.create(
            owner=self.student,
            subject=self.subject,
            title="Economics 101",
            file=ContentFile(b"%PDF-1.4", name="economics.pdf"),
            status=DocumentStatus.READY,
            parser_confidence_score=0.95,
            parser_strategy="legacy",
        )
        self.failed_document = Document.objects.create(
            owner=self.student,
            title="Broken textbook",
            file=ContentFile(b"%PDF-1.4", name="broken.pdf"),
            status=DocumentStatus.FAILED,
            parser_confidence_score=0.42,
            parser_warnings=["Could not detect reliable chapters."],
        )
        self.chapter = Chapter.objects.create(
            document=self.document,
            title="Supply and Demand",
            sequence_number=1,
            extracted_text="Supply and demand content.",
            chapter_objectives=["Explain the demand curve"],
        )
        self.concept = Concept.objects.create(
            chapter=self.chapter,
            title="Demand curve",
            sequence_number=1,
            summary="Demand curves can slope downward.",
        )
        ConceptLesson.objects.create(
            user=self.student,
            concept=self.concept,
            source_excerpt="Demand curve text.",
            explanation="A demand curve shows quantity demanded.",
            examples=["Higher prices may reduce demand."],
            next_action="ready_for_mcq",
        )
        QuizAttempt.objects.create(
            user=self.student,
            concept=self.concept,
            submitted_answers={},
            total_questions=1,
            correct_answers=1,
            score=100,
            passed=True,
        )
        self.unanswered_question = QuizQuestion.objects.create(
            concept=self.concept,
            question_text="What does a demand curve show?",
            option_a="Quantity demanded at different prices",
            option_b="Only production costs",
            option_c="Only government taxes",
            option_d="Only business profit",
            correct_option="A",
            explanation="A demand curve relates price and quantity demanded.",
            is_answered=False,
        )
        self.answered_question = QuizQuestion.objects.create(
            concept=self.concept,
            question_text="Which way can a typical demand curve slope?",
            option_a="Downward",
            option_b="Only vertical",
            option_c="Only horizontal",
            option_d="Never changes",
            correct_option="A",
            explanation="Typical demand curves slope downward.",
            is_answered=True,
        )
        ConceptProgress.objects.create(
            user=self.student,
            concept=self.concept,
            status=ProgressStatus.MASTERED,
            attempts_count=1,
            last_score=50,
            mastered_at=timezone.now(),
        )

    def test_normal_user_cannot_access_command_center_api(self) -> None:
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/admin/command-center/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_access_command_center_api(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/command-center/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Abbot Command Center")
        metrics = {metric["key"]: metric["value"] for metric in response.data["metrics"]}
        self.assertEqual(metrics["total_users"], 5)
        self.assertEqual(metrics["total_subjects"], 1)
        self.assertEqual(metrics["total_documents"], 2)
        self.assertEqual(metrics["total_chapters"], 1)
        self.assertEqual(metrics["total_concepts"], 1)
        self.assertEqual(metrics["total_quiz_attempts"], 1)
        self.assertEqual(metrics["total_tutor_sessions"], 1)
        self.assertEqual(metrics["failed_document_processing_count"], 1)
        self.assertEqual(metrics["low_confidence_parser_count"], 1)
        self.assertEqual(response.data["recent_uploaded_textbooks"][0]["owner_username"], "student")
        self.assertEqual(response.data["recent_failed_jobs"][0]["document_id"], self.failed_document.id)

    def test_staff_user_can_view_aggregated_user_analytics(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/analytics/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_users"], 5)
        countries = {row["label"]: row["value"] for row in response.data["users_by_country"]}
        roles = {row["label"]: row["value"] for row in response.data["users_by_role"]}
        self.assertGreaterEqual(countries["Lesotho"], 1)
        self.assertGreaterEqual(roles["student"], 1)
        self.assertGreaterEqual(response.data["textbook_uploads_over_time"][0]["uploads"], 1)
        self.assertGreaterEqual(response.data["concept_completions_over_time"][0]["completions"], 1)
        self.assertEqual(response.data["quiz_pass_fail_trends"][0]["passed"], 1)
        self.assertIn("aggregated", response.data["privacy_note"].lower())

    def test_staff_without_user_permission_cannot_manage_users(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/users/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permissioned_staff_can_search_and_filter_users(self) -> None:
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.client.force_authenticate(self.user_admin)

        response = self.client.get("/api/admin/users/", {"q": "student", "status": "inactive", "role": "non_staff"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        user = response.data["users"][0]
        self.assertEqual(user["username"], "student")
        self.assertFalse(user["is_active"])
        self.assertNotIn("password", user)

    def test_permissioned_staff_can_view_user_profile_summary(self) -> None:
        self.client.force_authenticate(self.user_admin)

        response = self.client.get(f"/api/admin/users/{self.student.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "student")
        self.assertNotIn("password", response.data)
        self.assertEqual(response.data["summary"]["subject_count"], 1)
        self.assertEqual(response.data["summary"]["document_count"], 2)
        self.assertEqual(response.data["summary"]["quiz_attempt_count"], 1)
        self.assertEqual(response.data["subjects"][0]["name"], "Economics")
        self.assertEqual(response.data["textbooks"][0]["title"], "Broken textbook")
        self.assertEqual(response.data["learning_progress"]["quiz_attempts"], 1)

    def test_permissioned_staff_can_deactivate_and_reactivate_user(self) -> None:
        self.client.force_authenticate(self.user_admin)

        deactivate_response = self.client.post(f"/api/admin/users/{self.student.id}/deactivate/")
        self.student.refresh_from_db()
        reactivate_response = self.client.post(f"/api/admin/users/{self.student.id}/reactivate/")
        self.student.refresh_from_db()

        self.assertEqual(deactivate_response.status_code, status.HTTP_200_OK)
        self.assertFalse(deactivate_response.data["is_active"])
        self.assertEqual(reactivate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.student.is_active)
        self.assertTrue(AdminAuditLog.objects.filter(action="user_deactivate", target_id=str(self.student.id)).exists())
        self.assertTrue(AdminAuditLog.objects.filter(action="user_reactivate", target_id=str(self.student.id)).exists())

    def test_admin_cannot_deactivate_self(self) -> None:
        self.client.force_authenticate(self.user_admin)

        response = self.client.post(f"/api/admin/users/{self.user_admin.id}/deactivate/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_without_document_permission_cannot_manage_textbooks(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/textbooks/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_textbook_admin_can_filter_textbooks(self) -> None:
        self.client.force_authenticate(self.textbook_admin)

        response = self.client.get("/api/admin/textbooks/", {"status": DocumentStatus.FAILED, "confidence": "low"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["textbooks"][0]["title"], "Broken textbook")
        self.assertTrue(response.data["textbooks"][0]["progress_exists"] is False)

    def test_textbook_admin_can_view_ordered_chapters_and_parser_warnings(self) -> None:
        Chapter.objects.create(
            document=self.document,
            title="Markets",
            sequence_number=2,
            extracted_text="Markets content.",
        )
        self.client.force_authenticate(self.textbook_admin)

        response = self.client.get(f"/api/admin/textbooks/{self.document.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([chapter["sequence_number"] for chapter in response.data["chapters"]], [1, 2])
        self.assertTrue(response.data["progress_exists"])
        self.assertEqual(response.data["progress_summary"]["concept_progress"], 1)

    def test_parser_preview_is_read_only_and_returns_proposals(self) -> None:
        self.client.force_authenticate(self.textbook_admin)

        from unittest.mock import patch

        text = "Chapter 1: Intro\nAlpha content.\nChapter 2: Next\nBeta content."
        with patch("core.views.extract_text_from_pdf", return_value=text):
            response = self.client.get(f"/api/admin/textbooks/{self.document.id}/parser-preview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["document_id"], self.document.id)
        self.assertEqual(len(response.data["current_stored_chapters"]), 1)
        self.assertEqual(response.data["legacy"]["accepted_chapter_count"], 2)
        self.assertEqual(Chapter.objects.filter(document=self.document).count(), 1)

    def test_reprocess_requires_confirmation_and_force_when_progress_exists(self) -> None:
        self.client.force_authenticate(self.textbook_admin)

        missing_confirm = self.client.post(f"/api/admin/textbooks/{self.document.id}/reprocess/", {})
        without_force = self.client.post(
            f"/api/admin/textbooks/{self.document.id}/reprocess/",
            {"confirm": True},
            format="json",
        )

        self.assertEqual(missing_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(without_force.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(without_force.data["requires_force_reset_progress"])

    def test_reprocess_queues_task_when_confirmed_with_force(self) -> None:
        self.client.force_authenticate(self.textbook_admin)

        from unittest.mock import patch

        with patch("core.views.extract_chapters_from_document.delay") as mock_delay:
            response = self.client.post(
                f"/api/admin/textbooks/{self.document.id}/reprocess/",
                {"confirm": True, "force_reset_progress": True},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(self.document.id)
        self.assertTrue(AdminAuditLog.objects.filter(action="textbook_reprocess_queued", target_id=str(self.document.id)).exists())

    def test_delete_textbook_requires_confirmation_and_cascades(self) -> None:
        self.client.force_authenticate(self.textbook_admin)

        missing_confirm = self.client.delete(f"/api/admin/textbooks/{self.document.id}/")
        confirmed = self.client.delete(f"/api/admin/textbooks/{self.document.id}/?confirm=true")

        self.assertEqual(missing_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(confirmed.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=self.document.id).exists())
        self.assertFalse(Chapter.objects.filter(id=self.chapter.id).exists())
        self.assertFalse(Concept.objects.filter(id=self.concept.id).exists())
        self.assertTrue(AdminAuditLog.objects.filter(action="textbook_deleted", target_id=str(self.document.id)).exists())

    def test_staff_without_quality_permission_cannot_use_concept_quality_tools(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/quality/concepts/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_quality_admin_can_view_concept_quality_by_textbook_and_chapter(self) -> None:
        self.client.force_authenticate(self.quality_admin)

        response = self.client.get(
            "/api/admin/quality/concepts/",
            {"document_id": self.document.id, "chapter_id": self.chapter.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        concept = response.data["concepts"][0]
        self.assertEqual(concept["title"], "Demand curve")
        self.assertEqual(concept["question_count"], 2)
        self.assertEqual(concept["unanswered_question_count"], 1)
        self.assertEqual(concept["quiz_attempt_count"], 1)
        self.assertEqual(concept["pass_rate"], 100.0)
        self.assertTrue(concept["possible_objective_match"])
        self.assertEqual(concept["matched_objective"], "Explain the demand curve")
        self.assertFalse(response.data["flagged_questions"]["flagging_available"])

    def test_quality_admin_can_view_commonly_failed_concepts(self) -> None:
        QuizAttempt.objects.create(
            user=self.student,
            concept=self.concept,
            submitted_answers={},
            total_questions=1,
            correct_answers=0,
            score=0,
            passed=False,
        )
        self.client.force_authenticate(self.quality_admin)

        response = self.client.get("/api/admin/quality/concepts/", {"issue": "failed"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["concepts"][0]["fail_count"], 1)
        self.assertEqual(response.data["commonly_failed_concepts"][0]["title"], "Demand curve")

    def test_regenerate_mcqs_requires_confirmation_and_preserves_answered_questions(self) -> None:
        self.client.force_authenticate(self.quality_admin)

        missing_confirm = self.client.post(f"/api/admin/quality/concepts/{self.concept.id}/regenerate-mcqs/", {})
        confirmed = self.client.post(
            f"/api/admin/quality/concepts/{self.concept.id}/regenerate-mcqs/",
            {"confirm": True},
            format="json",
        )

        self.assertEqual(missing_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        self.assertEqual(confirmed.data["deleted_count"], 1)
        self.assertFalse(QuizQuestion.objects.filter(id=self.unanswered_question.id).exists())
        self.assertTrue(QuizQuestion.objects.filter(id=self.answered_question.id).exists())
        self.assertTrue(QuizAttempt.objects.filter(concept=self.concept).exists())
        self.assertTrue(AdminAuditLog.objects.filter(action="mcq_regenerated", target_id=str(self.concept.id)).exists())

    def test_regenerate_tutor_requires_confirmation_and_preserves_progress(self) -> None:
        self.client.force_authenticate(self.quality_admin)

        missing_confirm = self.client.post(f"/api/admin/quality/concepts/{self.concept.id}/regenerate-tutor/", {})
        confirmed = self.client.post(
            f"/api/admin/quality/concepts/{self.concept.id}/regenerate-tutor/",
            {"confirm": True},
            format="json",
        )

        self.assertEqual(missing_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        self.assertEqual(confirmed.data["deleted_count"], 1)
        self.assertFalse(ConceptLesson.objects.filter(concept=self.concept).exists())
        self.assertTrue(ConceptProgress.objects.filter(concept=self.concept).exists())
        self.assertTrue(AdminAuditLog.objects.filter(action="tutor_lesson_regenerated", target_id=str(self.concept.id)).exists())

    def test_audit_log_requires_permission(self) -> None:
        self.client.force_authenticate(self.staff)

        response = self.client.get("/api/admin/audit-logs/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permissioned_admin_can_view_audit_logs(self) -> None:
        AdminAuditLog.objects.create(
            admin_user=self.user_admin,
            action="user_deactivate",
            target_type="user",
            target_id=str(self.student.id),
            description="Admin deactivated a test user.",
            metadata={"target_username": self.student.username},
            ip_address="127.0.0.1",
        )
        self.client.force_authenticate(self.user_admin)

        response = self.client.get("/api/admin/audit-logs/", {"q": "deactivated"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(response.data["logs"][0]["action"], "user_deactivate")
        self.assertEqual(response.data["logs"][0]["admin_username"], "user-admin")
