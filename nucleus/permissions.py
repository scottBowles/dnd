from typing import Any
from strawberry import BasePermission
from strawberry.types import Info


class IsStaff(BasePermission):
    message = "You must be a staff member to perform this action."

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        return info.context.request.user.is_staff


class IsSuperuser(BasePermission):
    message = "You must be a superuser to perform this action."

    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        return info.context.request.user.is_superuser


class IsLockUserOrSuperuserIfLocked(BasePermission):
    """
    Permission class for entities that implement locking.

    This must be applied to mutations that take an input object with an global id field
    named "id" that resolves to a node that implements locking.

    The permission will ensure that, if the node is locked, the user must be the lock user
    or a superuser.
    """

    message = "This object is locked and you are not the owner or a superuser."

    def has_permission(self, source: Any, info: Info, input, **kwargs) -> bool:
        try:
            global_id = input.id
            node = global_id.resolve_node_sync(info)

            return (
                node is None
                or node.lock_user is None
                or node.lock_user == info.context.request.user
                or info.context.request.user.is_superuser
            )
        except Exception:
            self.message = (
                "An error occurred while checking permissions in IsLockUserOrSuperuser."
            )
            return False
