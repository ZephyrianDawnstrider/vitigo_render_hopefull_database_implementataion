import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.core.exceptions import PermissionDenied

from settings.models import APIConfiguration, SocialMediaCredential
from settings.forms import APIConfigurationForm, SocialMediaCredentialForm
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class IntegrationSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Integration Settings")
                return handler403(request, exception="Access Denied")

            # Get existing configurations
            api_configs = APIConfiguration.objects.all()
            social_credentials = SocialMediaCredential.objects.all()
            
            # Initialize forms
            api_form = APIConfigurationForm()
            social_form = SocialMediaCredentialForm()

            context = {
                'api_configs': api_configs,
                'social_credentials': social_credentials,
                'api_form': api_form,
                'social_form': social_form,
                'form_errors': {},
            }

            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')

            template_path = get_template_path('integration/integration_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in IntegrationSettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading integration settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify integration settings")

            action = request.POST.get('action')

            if action == 'add_api_config':
                return self.handle_api_config(request)
            elif action == 'add_social_credential':
                return self.handle_social_credential(request)
            else:
                messages.error(request, "Invalid action specified")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error in IntegrationSettingsView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while saving settings")

        return redirect('settings:integration_settings')

    def handle_api_config(self, request):
        form = APIConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, "API configuration added successfully")
        else:
            request.session['form_errors'] = {'api_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:integration_settings')

    def handle_social_credential(self, request):
        form = SocialMediaCredentialForm(request.POST)
        if form.is_valid():
            credential = form.save(commit=False)
            credential.created_by = request.user
            credential.save()
            messages.success(request, "Social media credential added successfully")
        else:
            request.session['form_errors'] = {'social_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:integration_settings')
