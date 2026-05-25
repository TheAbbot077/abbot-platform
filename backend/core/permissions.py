from rest_framework import permissions


class IsStaffUser(permissions.BasePermission):
    """Allow access only to authenticated staff/admin users."""

    message = "Abbot Command Center is available only to staff administrators."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class CanManageUsers(permissions.BasePermission):
    """Allow user management only to superusers or staff with user-change permission."""

    message = "User management requires administrator permission."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and (user.is_superuser or user.has_perm("accounts.change_user"))
        )


class CanManageTextbooks(permissions.BasePermission):
    """Allow textbook/parser management to superusers or staff with document-change permission."""

    message = "Textbook management requires administrator permission."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and (user.is_superuser or user.has_perm("documents.change_document"))
        )


class CanManageQualityTools(permissions.BasePermission):
    """Allow concept and quiz quality tools only to trusted academic admins."""

    message = "Concept quality tools require administrator permission."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and (
                user.is_superuser
                or user.has_perm("learning.change_quizquestion")
                or user.has_perm("documents.change_concept")
            )
        )


class CanViewAuditLogs(permissions.BasePermission):
    """Allow audit log review only to superusers or staff with audit-log view permission."""

    message = "Audit logs require administrator permission."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and (user.is_superuser or user.has_perm("core.view_adminauditlog"))
        )
