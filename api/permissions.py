from rest_framework import permissions

class IsUserOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or staff members to access it.
    """
    def has_permission(self, request, view):
        # Allow staff members
        if request.user.is_staff:
            return True
            
        # For non-staff, check if they're accessing their own data
        user_id = view.kwargs.get('user_id')
        return str(request.user.id) == str(user_id)