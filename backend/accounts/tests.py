from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document, Subject

from .models import ThemeChoice, UserProfile, UserSettings


class AuthFlowApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="auth-student",
            email="auth@example.com",
            password="strong-password-123",
        )

    def test_signup_creates_user_and_starts_session(self) -> None:
        response = self.client.post(
            reverse("auth-signup"),
            {
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Student",
                "password": "strong-password-123",
                "confirm_password": "strong-password-123",
                "country": "Lesotho",
                "role": "student",
                "age_range": "16_18",
                "gender": "prefer_not_to_say",
                "education_level": "high_school",
                "subjects_of_interest": ["Math", "Economics"],
            },
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0) Chrome/125.0",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["email"], "new@example.com")
        user = get_user_model().objects.get(email="new@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Student")
        self.assertEqual(user.profile.country, "Lesotho")
        self.assertEqual(user.profile.role, "student")
        self.assertEqual(user.profile.age_range, "16_18")
        self.assertEqual(user.profile.browser, "Chrome")
        self.assertEqual(user.profile.login_count, 1)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

    def test_signup_requires_matching_password_confirmation(self) -> None:
        response = self.client.post(
            reverse("auth-signup"),
            {
                "email": "mismatch@example.com",
                "first_name": "Mismatch",
                "last_name": "Student",
                "password": "strong-password-123",
                "confirm_password": "different-password-123",
                "country": "Lesotho",
                "role": "student",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_starts_session(self) -> None:
        response = self.client.post(
            reverse("auth-login"),
            {"username": "auth-student", "password": "strong-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "auth-student")
        self.assertEqual(UserProfile.objects.get(user=self.user).login_count, 1)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

    def test_login_accepts_email_identifier(self) -> None:
        response = self.client.post(
            reverse("auth-login"),
            {"username": "auth@example.com", "password": "strong-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "auth-student")

    def test_user_can_logout_then_login_as_different_account(self) -> None:
        second_user = get_user_model().objects.create_user(
            username="second-student",
            email="second@example.com",
            password="strong-password-456",
        )
        self.client.login(username=self.user.username, password="strong-password-123")
        self.client.post(reverse("auth-logout"))

        response = self.client.post(
            reverse("auth-login"),
            {"username": second_user.email, "password": "strong-password-456"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], second_user.username)
        self.assertEqual(self.client.get(reverse("auth-me")).data["user"]["username"], second_user.username)

    def test_logout_clears_session(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")

        response = self.client.post(reverse("auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME].value, "")
        self.assertEqual(response.cookies[settings.CSRF_COOKIE_NAME].value, "")
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_page_session_invalidation_logout_behavior(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")

        logout_response = self.client.post(reverse("auth-logout"))
        me_response = self.client.get(reverse("auth-me"))

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_route_rejects_user_after_logout(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")
        self.client.post(reverse("auth-logout"))

        response = self.client.get(reverse("progress-dashboard"))

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_refresh_after_logout_does_not_restore_old_user(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")
        self.client.post(reverse("auth-logout"))

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["user"], None)

    def test_session_cookie_expires_at_browser_close(self) -> None:
        response = self.client.post(
            reverse("auth-login"),
            {"username": "auth-student", "password": "strong-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session_cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertEqual(session_cookie["expires"], "")
        self.assertEqual(session_cookie["max-age"], "")

    def test_new_browser_without_session_cookie_does_not_restore_old_user(self) -> None:
        self.client.post(
            reverse("auth-login"),
            {"username": "auth-student", "password": "strong-password-123"},
            format="json",
        )

        new_browser_client = APIClient()
        response = new_browser_client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["user"], None)

    def test_cached_frontend_user_data_does_not_count_as_authentication(self) -> None:
        response = self.client.get(
            reverse("progress-dashboard"),
            HTTP_X_CACHED_USER='{"username":"auth-student"}',
            HTTP_AUTHORIZATION="Bearer fake-client-cache-token",
        )

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_protected_route_requires_login(self) -> None:
        response = self.client.get(reverse("progress-dashboard"))

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, private")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

    def test_authenticated_api_response_has_no_store_headers(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")

        response = self.client.get(reverse("progress-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Cache-Control"], "no-store, no-cache, must-revalidate, private")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

    def test_expired_session_returns_clean_unauthorized_response(self) -> None:
        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["user"], None)

    def test_deleted_backend_session_redirects_api_to_unauthorized_state(self) -> None:
        self.client.login(username="auth-student", password="strong-password-123")
        Session.objects.all().delete()

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["user"], None)

    def test_second_user_same_browser_cannot_see_first_user_dashboard(self) -> None:
        second_user = get_user_model().objects.create_user(
            username="second-browser-user",
            email="second-browser@example.com",
            password="strong-password-456",
        )
        first_subject = Subject.objects.create(owner=self.user, name="First User Subject")
        Document.objects.create(
            owner=self.user,
            subject=first_subject,
            title="First User Private Textbook",
            file=SimpleUploadedFile("first-user.pdf", b"fake pdf content", content_type="application/pdf"),
        )

        self.client.login(username=self.user.username, password="strong-password-123")
        self.client.post(reverse("auth-logout"))
        login_response = self.client.post(
            reverse("auth-login"),
            {"username": second_user.email, "password": "strong-password-456"},
            format="json",
        )
        dashboard_response = self.client.get(reverse("progress-dashboard"))

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["user"]["username"], second_user.username)
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_response.data["documents"], [])


class UserSettingsApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="settings-student",
            email="settings@example.com",
            password="strong-password-123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_default_settings_are_created_for_user(self) -> None:
        response = self.client.get(reverse("auth-settings"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], ThemeChoice.BLACK_WHITE_GOLD)
        self.assertEqual(UserSettings.objects.get(user=self.user).theme, ThemeChoice.BLACK_WHITE_GOLD)

    def test_user_can_update_theme(self) -> None:
        response = self.client.patch(
            reverse("auth-settings"),
            {"theme": ThemeChoice.ROYAL_BLUE_WHITE_GOLD},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], ThemeChoice.ROYAL_BLUE_WHITE_GOLD)
        self.assertEqual(UserSettings.objects.get(user=self.user).theme, ThemeChoice.ROYAL_BLUE_WHITE_GOLD)

    def test_invalid_theme_is_rejected(self) -> None:
        response = self.client.patch(reverse("auth-settings"), {"theme": "orange"}, format="json")

        self.assertEqual(response.status_code, 400)
