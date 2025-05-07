# Python Standard Library imports
import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Django core imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.views.generic.edit import FormView

# Django REST Framework imports
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from doctor_management.models import DoctorProfile
from error_handling.views import handler403, handler404, handler500
from patient_management.models import MedicalHistory

from ..utils import get_template_path
from ..forms import AppointmentCreateForm, ReminderTemplateForm, ReminderConfigurationForm
from ..models import (
    Appointment,
    AppointmentReminder,
    CancellationReason,
    DoctorTimeSlot,
    ReminderConfiguration,
    ReminderTemplate,
)

# Logger configuration
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()


class AppointmentReminderView(LoginRequiredMixin, ListView):
    model = ReminderTemplate
    context_object_name = 'reminder_templates'

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(self.request.user, 'appointment_management'):
            messages.error(request, "You don't have permission to access appointment reminders")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('appointment_reminders.html', self.request.user.role, 'appointment_management')]

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            
            # Add reminder-related data
            context.update({
                'appointment_types': dict(Appointment.APPOINTMENT_TYPES),
                'reminder_configs': ReminderConfiguration.objects.select_related().all(),
                
                # Statistics
                'total_templates': ReminderTemplate.objects.count(),
                'active_templates': ReminderTemplate.objects.filter(is_active=True).count(),
                'total_reminders': AppointmentReminder.objects.count(),
                'pending_reminders': AppointmentReminder.objects.filter(status='PENDING').count(),
            })
            
            return context
            
        except Exception as e:
            logger.error(f"Error in AppointmentReminderView context: {str(e)}")
            messages.error(self.request, "Error loading reminder data")
            return {}
        

class CreateReminderTemplateView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            form = ReminderTemplateForm(request.POST)
            if form.is_valid():
                template = form.save(commit=False)
                template.created_by = request.user
                template.save()
                
                messages.success(request, 'Reminder template created successfully!')
                return redirect('appointment_reminders')
            else:
                messages.error(request, 'Failed to create template. Please check the form data.')
                return redirect('appointment_reminders')
        except Exception as e:
            logger.error(f"Error creating reminder template: {str(e)}")
            messages.error(request, 'An error occurred while creating the template.')
            return redirect('appointment_reminders')


class ConfigureReminderSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        configs = ReminderConfiguration.objects.all()
        return JsonResponse({
            'configs': list(configs.values('id', 'appointment_type', 'reminder_types', 'is_active')),
            'templates': list(ReminderTemplate.objects.filter(is_active=True).values('id', 'name'))
        })

    def post(self, request):
        try:
            appointment_type = request.POST.get('appointment_type')
            template_ids = request.POST.getlist('templates')
            
            # Fix: Properly handle notification methods
            reminder_types = {
                'email': request.POST.get('notification_email') == 'on',
                'sms': request.POST.get('notification_sms') == 'on'
            }
            
            # Fix: Properly handle active status
            is_active = request.POST.get('is_active') == 'on'

            config, created = ReminderConfiguration.objects.update_or_create(
                appointment_type=appointment_type,
                defaults={
                    'reminder_types': reminder_types,
                    'is_active': is_active
                }
            )
            
            # Update templates
            config.templates.set(template_ids)
            
            messages.success(request, 'Reminder settings updated successfully!')
            return redirect('appointment_reminders')
            
        except Exception as e:
            logger.error(f"Error configuring reminder settings: {str(e)}")
            messages.error(request, 'Failed to update reminder settings')
            return redirect('appointment_reminders')

class DeleteReminderTemplateView(LoginRequiredMixin, View):
    def post(self, request, template_id):
        try:
            template = get_object_or_404(ReminderTemplate, id=template_id)
            template_name = template.name
            
            # Check if template is being used in any configurations
            if template.configurations.exists():
                messages.error(request, 'Cannot delete template as it is being used in active configurations.')
                return redirect('appointment_reminders')
            
            template.delete()
            messages.success(request, f'Template "{template_name}" deleted successfully.')
            return redirect('appointment_reminders')
            
        except Exception as e:
            logger.error(f"Error deleting reminder template: {str(e)}")
            messages.error(request, 'Failed to delete template.')
            return redirect('appointment_reminders')

class DeleteReminderConfigurationView(LoginRequiredMixin, View):
    def post(self, request, config_id):
        try:
            config = get_object_or_404(ReminderConfiguration, id=config_id)
            appointment_type = config.get_appointment_type_display()
            
            # Remove template associations first
            config.templates.clear()
            config.delete()
            
            messages.success(request, f'Configuration for "{appointment_type}" deleted successfully.')
            return redirect('appointment_reminders')
            
        except Exception as e:
            logger.error(f"Error deleting reminder configuration: {str(e)}")
            messages.error(request, 'Failed to delete configuration.')
            return redirect('appointment_reminders')

class EditReminderTemplateView(LoginRequiredMixin, View):
    def get(self, request, template_id):
        template = get_object_or_404(ReminderTemplate, id=template_id)
        return JsonResponse({
            'id': template.id,
            'name': template.name,
            'days_before': template.days_before,
            'hours_before': template.hours_before,
            'message_template': template.message_template,
            'is_active': template.is_active,
        })
    
    def post(self, request, template_id):
        try:
            template = get_object_or_404(ReminderTemplate, id=template_id)
            form = ReminderTemplateForm(request.POST, instance=template)
            
            if form.is_valid():
                template = form.save()
                messages.success(request, f'Template "{template.name}" updated successfully.')
                return redirect('appointment_reminders')
            else:
                messages.error(request, 'Failed to update template. Please check the form data.')
                return redirect('appointment_reminders')
                
        except Exception as e:
            logger.error(f"Error updating reminder template: {str(e)}")
            messages.error(request, 'Failed to update template.')
            return redirect('appointment_reminders')

class EditReminderConfigurationView(LoginRequiredMixin, View):
    def get(self, request, config_id):
        config = get_object_or_404(ReminderConfiguration, id=config_id)
        return JsonResponse({
            'id': config.id,
            'appointment_type': config.appointment_type,
            'templates': list(config.templates.values_list('id', flat=True)),
            'reminder_types': config.reminder_types,
            'is_active': config.is_active
        })

    def post(self, request, config_id):
        try:
            config = get_object_or_404(ReminderConfiguration, id=config_id)
            
            # Update basic fields
            config.appointment_type = request.POST.get('appointment_type')
            config.reminder_types = {
                'email': request.POST.get('notification_email') == 'on',
                'sms': request.POST.get('notification_sms') == 'on'
            }
            config.is_active = request.POST.get('is_active') == 'on'
            
            # Update template associations
            template_ids = request.POST.getlist('templates')
            
            with transaction.atomic():
                config.save()
                config.templates.set(template_ids)
            
            messages.success(request, f'Configuration for "{config.get_appointment_type_display()}" updated successfully.')
            return redirect('appointment_reminders')
            
        except Exception as e:
            logger.error(f"Error updating reminder configuration: {str(e)}")
            messages.error(request, 'Failed to update configuration.')
            return redirect('appointment_reminders')
