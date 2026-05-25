from __future__ import annotations

from django.utils import timezone

from .models import UserProfile, UserRole


def profile_analytics_from_request(request) -> dict[str, str]:
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return {
        "timezone": str(request.data.get("timezone", "")).strip()[:80],
        "device_type": _device_type(user_agent),
        "browser": _browser(user_agent),
        "operating_system": _operating_system(user_agent),
    }


def record_login_activity(user, request) -> None:
    profile = _profile_for_user(user)

    now = timezone.now()
    request_metadata = profile_analytics_from_request(request)
    profile.last_login_at = now
    profile.last_active_at = now
    profile.login_count += 1
    for field, value in request_metadata.items():
        if value:
            setattr(profile, field, value)
    profile.save(
        update_fields=[
            "last_login_at",
            "last_active_at",
            "login_count",
            "timezone",
            "device_type",
            "browser",
            "operating_system",
        ]
    )


def record_active(user) -> None:
    profile = _profile_for_user(user)
    profile.last_active_at = timezone.now()
    profile.save(update_fields=["last_active_at"])


def _device_type(user_agent: str) -> str:
    lowered = user_agent.lower()
    if "mobile" in lowered or "iphone" in lowered or "android" in lowered:
        return "mobile"
    if "ipad" in lowered or "tablet" in lowered:
        return "tablet"
    return "desktop" if user_agent else ""


def _browser(user_agent: str) -> str:
    lowered = user_agent.lower()
    if "edg/" in lowered:
        return "Edge"
    if "chrome/" in lowered and "chromium" not in lowered:
        return "Chrome"
    if "firefox/" in lowered:
        return "Firefox"
    if "safari/" in lowered and "chrome/" not in lowered:
        return "Safari"
    return "Unknown" if user_agent else ""


def _operating_system(user_agent: str) -> str:
    lowered = user_agent.lower()
    if "windows" in lowered:
        return "Windows"
    if "mac os" in lowered:
        return "macOS"
    if "android" in lowered:
        return "Android"
    if "iphone" in lowered or "ipad" in lowered:
        return "iOS"
    if "linux" in lowered:
        return "Linux"
    return "Unknown" if user_agent else ""


def _profile_for_user(user) -> UserProfile:
    profile, _created = UserProfile.objects.get_or_create(
        user=user,
        defaults={"country": "not_provided", "role": UserRole.STUDENT},
    )
    return profile
