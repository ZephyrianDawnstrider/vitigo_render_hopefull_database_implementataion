import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.core.exceptions import PermissionDenied

from settings.models import SecurityConfiguration, AuthenticationProvider
from settings.forms import SecurityConfigurationForm, AuthenticationProviderForm
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class SecuritySettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Security Settings")
                return handler403(request, exception="Access Denied")

            # Get existing configurations
            security_config = SecurityConfiguration.objects.first()
            auth_providers = AuthenticationProvider.objects.all()
            
            # Initialize forms
            security_form = SecurityConfigurationForm(instance=security_config)
            auth_provider_form = AuthenticationProviderForm()

            context = {
                'security_config': security_config,
                'auth_providers': auth_providers,
                'security_form': security_form,
                'auth_provider_form': auth_provider_form,
                'form_errors': {},
            }

            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')

            template_path = get_template_path('security/security_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in SecuritySettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading security settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify security settings")

            action = request.POST.get('action')

            if action == 'update_security_config':
                return self.handle_security_config(request)
            elif action == 'add_auth_provider':
                return self.handle_auth_provider(request)
            else:
                messages.error(request, "Invalid action specified")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error in SecuritySettingsView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while saving settings")

        return redirect('settings:security_settings')

    def handle_security_config(self, request):
        instance = SecurityConfiguration.objects.first()
        form = SecurityConfigurationForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Security configuration updated successfully")
        else:
            request.session['form_errors'] = {'security_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:security_settings')

    def handle_auth_provider(self, request):
        form = AuthenticationProviderForm(request.POST)
        if form.is_valid():
            provider = form.save(commit=False)
            provider.created_by = request.user
            provider.save()
            messages.success(request, "Authentication provider added successfully")
        else:
            request.session['form_errors'] = {'auth_provider_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:security_settings')
