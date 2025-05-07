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
from ..forms import AppointmentCreateForm
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


class AppointmentDashboardView(LoginRequiredMixin, ListView):
    model = Appointment
    context_object_name = 'appointments'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'appointment_management'):
            messages.error(request, "You don't have permission to access Appointments")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.request.user.role.name == 'PATIENT':
            return ['patient/appointment_management/appointments/appointment_dashboard.html']
        return [get_template_path('dashboard/dashboard.html', self.request.user.role, 'appointment_management')]

    def get_queryset(self):
        queryset = Appointment.objects.select_related(
            'patient',
            'doctor',
            'time_slot'
        )
        
        # Filter appointments to only those of the logged-in patient if user is a patient
        if self.request.user.role.name == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user)
        
        # Get filter parameters from URL
        filters = {}
        priority = self.request.GET.get('priority')
        status = self.request.GET.get('status')
        date = self.request.GET.get('date')
        doctor = self.request.GET.get('doctor')
        # Remove patient filter for patients themselves
        # patient = self.request.GET.get('patient')
        appointment_type = self.request.GET.get('appointment_type')
        search = self.request.GET.get('search')
        
        # Apply filters
        if priority:
            filters['priority'] = priority
        if status:
            filters['status'] = status
        if date:
            filters['date'] = date
        if doctor:
            filters['doctor_id'] = doctor
        # Do not allow patient filter for patients themselves
        # if patient:
        #     filters['patient_id'] = patient
        if appointment_type:
            filters['appointment_type'] = appointment_type
            
        # Apply search query
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__email__icontains=search) |
                Q(doctor__first_name__icontains=search) |
                Q(doctor__last_name__icontains=search) |
                Q(doctor__email__icontains=search) |
                Q(notes__icontains=search)
            )
            
        return queryset.filter(**filters).order_by('-date', '-time_slot__start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        # Basic statistics
        if self.request.user.role.name == 'PATIENT':
            context.update({
                'total_appointments': Appointment.objects.filter(patient=self.request.user).count(),
                'pending_appointments': Appointment.objects.filter(patient=self.request.user, status='PENDING').count(),
                'completed_appointments': Appointment.objects.filter(patient=self.request.user, status='COMPLETED').count(),
                'today_appointments': Appointment.objects.filter(patient=self.request.user, date=today).count(),
            })
        else:
            context.update({
                'total_appointments': Appointment.objects.count(),
                'pending_appointments': Appointment.objects.filter(status='PENDING').count(),
                'completed_appointments': Appointment.objects.filter(status='COMPLETED').count(),
                'today_appointments': Appointment.objects.filter(date=today).count(),
            })
            
        # Current filters for template
        context.update({
            'current_filters': {
                'priority': self.request.GET.get('priority', ''),
                'status': self.request.GET.get('status', ''),
                'date': self.request.GET.get('date', ''),
                'search': self.request.GET.get('search', ''),
            },
        })
        
        context.update({
            # Add choices for filter dropdowns
            'status_choices': Appointment.STATUS_CHOICES,
            'priority_choices': Appointment.PRIORITY_CHOICES,
            'appointment_type_choices': Appointment.APPOINTMENT_TYPES,
            
            # Add available doctors and patients for filters only if not patient
            'doctors': User.objects.filter(role__name='DOCTOR').order_by('first_name') if self.request.user.role.name != 'PATIENT' else None,
            'patients': User.objects.filter(role__name='PATIENT').order_by('first_name') if self.request.user.role.name != 'PATIENT' else None,
            
            # Current filter values
            'current_filters': {
                'priority': self.request.GET.get('priority', ''),
                'status': self.request.GET.get('status', ''),
                'date': self.request.GET.get('date', ''),
                'doctor': self.request.GET.get('doctor', ''),
                # 'patient': self.request.GET.get('patient', ''),  # Removed for patients
                'appointment_type': self.request.GET.get('appointment_type', ''),
                'search': self.request.GET.get('search', ''),
            }
        })
        
        return context
