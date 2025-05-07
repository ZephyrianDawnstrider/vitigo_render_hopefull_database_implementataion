from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from access_control.permissions import PermissionManager
from error_handling.views import handler403
from settings.models import (
    SettingCategory,
    SystemConfiguration,
    SecurityConfiguration
)

from access_control.models import Role

def get_template_path(base_template, role, module='settings'):
    """
    Simple template path resolver based on user role
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    return f'{role_folder}/{module}/{base_template}'

class SettingsManagementView(View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Settings")
                return handler403(request, exception="Access Denied")

            template_path = get_template_path('settings_dashboard.html', request.user.role, 'settings')
            return render(request, template_path, {})

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('dashboard')
