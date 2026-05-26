from django.conf import settings
from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, response, status, views

from .analytics import profile_analytics_from_request, record_active, record_login_activity
from .models import UserSettings
from .serializers import LoginSerializer, SignupSerializer, UserSerializer, UserSettingsSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return response.Response({"detail": "CSRF cookie set."})


class CurrentUserView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return response.Response({"user": None}, status=status.HTTP_401_UNAUTHORIZED)

        record_active(request.user)
        return response.Response({"user": UserSerializer(request.user).data})


class UserSettingsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        settings, _created = UserSettings.objects.get_or_create(user=request.user)
        return response.Response(UserSettingsSerializer(settings).data)

    def patch(self, request):
        settings, _created = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data)


@method_decorator(csrf_exempt, name="dispatch")
class SignupView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        profile_metadata = profile_analytics_from_request(request)
        for field, value in profile_metadata.items():
            if value:
                setattr(user.profile, field, value)
        user.profile.save(update_fields=["timezone", "device_type", "browser", "operating_system"])
        login(request, user)
        record_login_activity(user, request)
        get_token(request)
        return response.Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        record_login_activity(user, request)
        get_token(request)
        return response.Response({"user": UserSerializer(user).data})


class LogoutView(views.APIView):
    def post(self, request):
        logout(request)
        logout_response = response.Response({"detail": "Logged out."})
        logout_response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path=settings.SESSION_COOKIE_PATH,
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        logout_response.delete_cookie(
            settings.CSRF_COOKIE_NAME,
            path=settings.CSRF_COOKIE_PATH,
            domain=settings.CSRF_COOKIE_DOMAIN,
            samesite=settings.CSRF_COOKIE_SAMESITE,
        )
        return logout_response
