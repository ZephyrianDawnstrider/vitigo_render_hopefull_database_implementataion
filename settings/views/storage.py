import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import requests

from settings.forms import CloudStorageProviderForm
from settings.models import CloudStorageProvider
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class StorageSettingsView(LoginRequiredMixin, View):
    @method_decorator(csrf_protect)
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Storage Settings")
                return handler403(request, exception="Access Denied")

            storage_provider = CloudStorageProvider.objects.first()
            form = CloudStorageProviderForm(instance=storage_provider)

            context = {
                'form': form,
                'active_section': 'storage'
            }

            template_path = get_template_path('storage/storage_settings.html', request.user.role)
            return render(request, template_path, context)
        except Exception as e:
            logger.error(f"Error in StorageSettingsView GET: {str(e)}")
            messages.error(request, "An error occurred while loading storage settings")
            return redirect('dashboard')

    @method_decorator(csrf_protect)
    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to modify Storage Settings")
                return handler403(request, exception="Access Denied")

            storage_provider = CloudStorageProvider.objects.first()
            form = CloudStorageProviderForm(request.POST, instance=storage_provider)
            
            if form.is_valid():
                form.save()
                messages.success(request, "Storage configuration updated successfully")
            else:
                error_messages = []
                for field, errors in form.errors.items():
                    field_name = form[field].label or field
                    error_messages.append(f"{field_name}: {', '.join(errors)}")
                messages.error(request, "Invalid storage configuration: " + " | ".join(error_messages))

            return redirect('settings:storage_settings')

        except Exception as e:
            logger.error(f"Error in StorageSettingsView POST: {str(e)}")
            messages.error(request, "An error occurred while saving storage settings")
            return redirect('settings:storage_settings')