from typing import Any
from strawberry_django_plus.gql import BasePermission
from strawberry.types import Info


class IsStaff(BasePermission):
    message = "You must be a staff member to perform this action."

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        return info.context.request.user.is_staff


class IsSuperuser(BasePermission):
    message = "You must be a superuser to perform this action."

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        return info.context.request.user.is_superuser
