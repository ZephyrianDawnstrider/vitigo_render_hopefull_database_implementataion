# Python Standard Library imports
import logging
from datetime import datetime

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    TeleconsultationSession,
    TeleconsultationPrescription,
    TeleconsultationFile,
    TeleconsultationFeedback,
    TelemedicinevirtualWaitingRoom
)

# Logger configuration
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module=''):
    """
    Resolves template path based on user role.
    Now uses the template_folder from Role model.
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        # Fallback for any legacy code
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    if module:
        return f'{role_folder}/{module}/{base_template}'
    return f'{role_folder}/{base_template}'

class TelemedicineManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'telemedicine_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to access Telemedicine Management")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('telemedicine_dashboard.html', self.request.user.role, 'telemedicine_management')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            # Get filter parameters from URL
            filters = {}
            status = request.GET.get('status')
            date = request.GET.get('date')
            search = request.GET.get('search')
            doctor = request.GET.get('doctor')
            patient = request.GET.get('patient')

            # Base queryset
            teleconsultations = TeleconsultationSession.objects.select_related('patient', 'doctor')
            
            # Apply filters
            if status:
                filters['status'] = status
            if date:
                filters['scheduled_start__date'] = date
            if doctor:
                filters['doctor_id'] = doctor
            if patient:
                filters['patient_id'] = patient

            # Apply search
            if search:
                teleconsultations = teleconsultations.filter(
                    Q(patient__user__first_name__icontains=search) |
                    Q(patient__user__last_name__icontains=search) |
                    Q(doctor__first_name__icontains=search) |
                    Q(doctor__last_name__icontains=search) |
                    Q(notes__icontains=search)
                )

            teleconsultations = teleconsultations.filter(**filters)

            # Fetch related data
            prescriptions = TeleconsultationPrescription.objects.all()
            files = TeleconsultationFile.objects.all()
            feedbacks = TeleconsultationFeedback.objects.all()
            waiting_rooms = TelemedicinevirtualWaitingRoom.objects.all()

            # Calculate statistics
            total_teleconsultations = teleconsultations.count()
            total_prescriptions = prescriptions.count()
            total_files = files.count()
            total_feedbacks = feedbacks.count()
            total_waiting_rooms = waiting_rooms.count()

            # Pagination for teleconsultation sessions
            paginator = Paginator(teleconsultations, 10)  # Show 10 teleconsultations per page
            page = request.GET.get('page')
            try:
                teleconsultations = paginator.page(page)
            except PageNotAnInteger:
                teleconsultations = paginator.page(1)
            except EmptyPage:
                teleconsultations = paginator.page(paginator.num_pages)

            # Context data to be passed to the template
            context = {
                'teleconsultations': teleconsultations,
                'prescriptions': prescriptions,
                'files': files,
                'feedbacks': feedbacks,
                'waiting_rooms': waiting_rooms,
                'total_teleconsultations': total_teleconsultations,
                'total_prescriptions': total_prescriptions,
                'total_files': total_files,
                'total_feedbacks': total_feedbacks,
                'total_waiting_rooms': total_waiting_rooms,
                'paginator': paginator,
                'page_obj': teleconsultations,
                'current_filters': {
                    'status': status,
                    'date': date,
                    'doctor': doctor,
                    'patient': patient,
                    'search': search
                },
                'user_role': request.user.role,  # Add user role to context
            }

            return render(request, template_path, context)

        except Exception as e:
            logger.exception(f"Error in TelemedicineManagementView: {str(e)}")
            return handler500(request, exception=str(e))