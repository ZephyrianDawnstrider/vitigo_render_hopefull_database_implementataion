# views.py
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from settings.forms import LoggingConfigurationForm, CacheConfigurationForm, BackupConfigurationForm
from settings.models import LoggingConfiguration, CacheConfiguration, BackupConfiguration
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class InfrastructureSettingsView(LoginRequiredMixin, View):
    @method_decorator(csrf_protect)
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Infrastructure Settings")
                return handler403(request, exception="Access Denied")

            logging_config = LoggingConfiguration.objects.first()
            cache_config = CacheConfiguration.objects.first()
            backup_config = BackupConfiguration.objects.first()

            context = {
                'logging_form': LoggingConfigurationForm(instance=logging_config),
                'cache_form': CacheConfigurationForm(instance=cache_config),
                'backup_form': BackupConfigurationForm(instance=backup_config),
                'active_section': 'infrastructure'
            }

            template_path = get_template_path('infrastructure/infrastructure_settings.html', request.user.role)
            return render(request, template_path, context)
        except Exception as e:
            logger.error(f"Error in InfrastructureSettingsView GET: {str(e)}")
            messages.error(request, "An error occurred while loading infrastructure settings")
            return redirect('dashboard')

    @method_decorator(csrf_protect)
    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to modify Infrastructure Settings")
                return handler403(request, exception="Access Denied")

            form_type = request.POST.get('form_type')
            
            if form_type == 'logging':
                return self._handle_logging_form(request)
            elif form_type == 'cache':
                return self._handle_cache_form(request)
            elif form_type == 'backup':
                return self._handle_backup_form(request)
            else:
                messages.error(request, "Invalid form submission")
                return redirect('settings:infrastructure_settings')

        except Exception as e:
            logger.error(f"Error in InfrastructureSettingsView POST: {str(e)}")
            messages.error(request, "An error occurred while saving infrastructure settings")
            return redirect('settings:infrastructure_settings')

    def _handle_logging_form(self, request):
        instance = LoggingConfiguration.objects.first()
        form = LoggingConfigurationForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Logging configuration updated successfully")
        else:
            # Create detailed error message
            error_messages = []
            for field, errors in form.errors.items():
                field_name = form[field].label or field
                error_messages.append(f"{field_name}: {', '.join(errors)}")
            messages.error(request, "Invalid logging configuration: " + " | ".join(error_messages))
        return redirect('settings:infrastructure_settings')

    def _handle_cache_form(self, request):
        instance = CacheConfiguration.objects.first()
        form = CacheConfigurationForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Cache configuration updated successfully")
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_name = form[field].label or field
                error_messages.append(f"{field_name}: {', '.join(errors)}")
            messages.error(request, "Invalid cache configuration: " + " | ".join(error_messages))
        return redirect('settings:infrastructure_settings')

    def _handle_backup_form(self, request):
        instance = BackupConfiguration.objects.first()
        form = BackupConfigurationForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Backup configuration updated successfully")
        else:
            error_messages = []
            for field, errors in form.errors.items():
                field_name = form[field].label or field
                error_messages.append(f"{field_name}: {', '.join(errors)}")
            messages.error(request, "Invalid backup configuration: " + " | ".join(error_messages))
        return redirect('settings:infrastructure_settings')