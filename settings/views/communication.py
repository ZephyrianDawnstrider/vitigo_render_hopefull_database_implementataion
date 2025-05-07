import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import PermissionDenied

from settings.models import EmailConfiguration, SMSProvider, NotificationProvider
from settings.forms import (
    EmailConfigurationForm, SMSProviderForm, NotificationProviderForm
)
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class CommunicationSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Communication Settings")
                return handler403(request, exception="Access Denied")

            # Get existing configurations
            email_configs = EmailConfiguration.objects.all()
            sms_providers = SMSProvider.objects.all()
            notification_providers = NotificationProvider.objects.all()

            # Initialize forms
            email_form = EmailConfigurationForm()
            sms_form = SMSProviderForm()
            notification_form = NotificationProviderForm()

            context = {
                'email_configs': email_configs,
                'sms_providers': sms_providers,
                'notification_providers': notification_providers,
                'email_form': email_form,
                'sms_form': sms_form,
                'notification_form': notification_form,
                'form_errors': {},
            }

            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')

            template_path = get_template_path('communication/communication_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in CommunicationSettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading communication settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify communication settings")

            action = request.POST.get('action')

            if action == 'add_email_config':
                return self.handle_email_config(request)
            elif action == 'add_sms_provider':
                return self.handle_sms_provider(request)
            elif action == 'add_notification_provider':
                return self.handle_notification_provider(request)
            else:
                messages.error(request, "Invalid action specified")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error in CommunicationSettingsView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while saving settings")

        return redirect('settings:communication_settings')

    def handle_email_config(self, request):
        form = EmailConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, "Email configuration added successfully")
        else:
            request.session['form_errors'] = {'email_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:communication_settings')

    def handle_sms_provider(self, request):
        form = SMSProviderForm(request.POST)
        if form.is_valid():
            provider = form.save(commit=False)
            provider.created_by = request.user
            provider.save()
            messages.success(request, "SMS provider added successfully")
        else:
            request.session['form_errors'] = {'sms_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:communication_settings')

    def handle_notification_provider(self, request):
        form = NotificationProviderForm(request.POST)
        if form.is_valid():
            provider = form.save(commit=False)
            provider.created_by = request.user
            provider.save()
            messages.success(request, "Notification provider added successfully")
        else:
            request.session['form_errors'] = {'notification_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:communication_settings')
