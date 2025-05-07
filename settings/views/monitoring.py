import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.core.exceptions import PermissionDenied

from settings.models import MonitoringConfiguration, AnalyticsConfiguration
from settings.forms import MonitoringConfigurationForm, AnalyticsConfigurationForm
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class MonitoringSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Monitoring Settings")
                return handler403(request, exception="Access Denied")

            # Get existing configurations
            monitoring_configs = MonitoringConfiguration.objects.all()
            analytics_configs = AnalyticsConfiguration.objects.all()
            
            # Initialize forms
            monitoring_form = MonitoringConfigurationForm()
            analytics_form = AnalyticsConfigurationForm()

            context = {
                'monitoring_configs': monitoring_configs,
                'analytics_configs': analytics_configs,
                'monitoring_form': monitoring_form,
                'analytics_form': analytics_form,
                'form_errors': {},
            }

            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')

            template_path = get_template_path('monitoring/monitoring_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in MonitoringSettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading monitoring settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify monitoring settings")

            action = request.POST.get('action')

            if action == 'add_monitoring_config':
                return self.handle_monitoring_config(request)
            elif action == 'add_analytics_config':
                return self.handle_analytics_config(request)
            else:
                messages.error(request, "Invalid action specified")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error in MonitoringSettingsView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while saving settings")

        return redirect('settings:monitoring_settings')

    def handle_monitoring_config(self, request):
        form = MonitoringConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, "Monitoring configuration added successfully")
        else:
            request.session['form_errors'] = {'monitoring_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:monitoring_settings')

    def handle_analytics_config(self, request):
        form = AnalyticsConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()
            messages.success(request, "Analytics configuration added successfully")
        else:
            request.session['form_errors'] = {'analytics_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:monitoring_settings')
