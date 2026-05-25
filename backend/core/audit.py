from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AnonymousUser

from .models import AdminAuditLog


def log_admin_action(
    *,
    request=None,
    admin_user=None,
    action: str,
    target_type: str,
    target_id: int | str | None,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> AdminAuditLog:
    """Record sensitive admin or account-impacting actions in one consistent format."""

    acting_user = admin_user or getattr(request, "user", None)
    if isinstance(acting_user, AnonymousUser) or not getattr(acting_user, "is_authenticated", False):
        acting_user = None

    return AdminAuditLog.objects.create(
        admin_user=acting_user,
        action=action,
        target_type=target_type,
        target_id="" if target_id is None else str(target_id),
        description=description,
        metadata=metadata or {},
        ip_address=_client_ip(request),
    )


def _client_ip(request) -> str | None:
    if request is None:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")
