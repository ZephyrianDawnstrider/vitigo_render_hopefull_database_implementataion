from django.core.cache import cache
from .models import ModulePermission, Role

class PermissionManager:
    @classmethod
    def check_module_access(cls, user, module_name):
        """
        Check if user has access to a specific module
        Returns True if user has access, False otherwise
        """
        try:
            permission = ModulePermission.objects.get(
                role=user.role,
                module__name=module_name,
                module__is_active=True
            )
            return permission.can_access
        except ModulePermission.DoesNotExist:
            return False

    @classmethod
    def check_module_modify(cls, user, module_name):
        """
        Check if user has modify permission for a specific module
        Returns True if user can modify, False otherwise
        """
        try:
            permission = ModulePermission.objects.get(
                role=user.role,
                module__name=module_name,
                module__is_active=True
            )
            return permission.can_modify
        except ModulePermission.DoesNotExist:
            return False

    @classmethod
    def check_module_delete(cls, user, module_name):
        """
        Check if user has delete permission for a specific module
        Returns True if user can delete, False otherwise
        """
        try:
            permission = ModulePermission.objects.get(
                role=user.role,
                module__name=module_name,
                module__is_active=True
            )
            return permission.can_delete
        except ModulePermission.DoesNotExist:
            return False