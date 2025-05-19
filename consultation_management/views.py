# Django imports 
import logging
from datetime import datetime
from django.utils import timezone  

# Standard library imports
from django.views.generic import ListView, View, DetailView, CreateView, UpdateView
from django.db.models import Count, Avg, Q, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from datetime import timedelta
from django.db import transaction
from django.urls import reverse_lazy
from django.http import Http404
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib.auth.mixins import UserPassesTestMixin
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# Local application imports
from .models import (
    Consultation, DoctorPrivateNotes, ConsultationType,
    ConsultationPriority, PaymentStatus, Prescription, PrescriptionTemplate, ConsultationFeedback, StaffInstruction, TemplateItem, PrescriptionItem, TreatmentPlan, TreatmentPlanItem
)
from .forms import ConsultationForm
from .utils import get_template_path
from access_control.models import Role
from access_control.permissions import PermissionManager
from stock_management.models import StockItem
from pharmacy_management.models import Medication
from error_handling.views import handler403, handler404, handler500
from phototherapy_management.models import PhototherapyPlan, PhototherapySession

logger = logging.getLogger(__name__)
User = get_user_model()

from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
from appointment_management.models import DoctorTimeSlot, Center

@method_decorator(require_GET, name='dispatch')
class DoctorClinicsView(LoginRequiredMixin, View):
    def get(self, request):
        user_id = request.GET.get('user_id')
        if not user_id:
            logger.warning("DoctorClinicsView: Missing user_id parameter")
            return JsonResponse({'error': 'Missing user_id parameter'}, status=400)
        try:
            doctor = User.objects.get(pk=user_id, role__name='DOCTOR')
            centers = DoctorTimeSlot.objects.filter(doctor=doctor).values('center__id', 'center__name').distinct()
            clinics_data = [{'id': center['center__id'], 'name': center['center__name']} for center in centers]
            return JsonResponse({'clinics': clinics_data})
        except User.DoesNotExist:
            logger.warning(f"DoctorClinicsView: Doctor with user_id {user_id} not found")
            return JsonResponse({'error': 'Doctor not found'}, status=404)
        except Exception as e:
            logger.error(f"DoctorClinicsView: Internal server error for doctor {user_id}: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_centers(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({"error": "user_id parameter is required"}, status=400)
    try:
        doctor = User.objects.get(id=user_id)
        if doctor.role.name != 'DOCTOR':
            return Response({"error": "User is not a doctor"}, status=400)
    except User.DoesNotExist:
        return Response({"error": "Doctor not found"}, status=404)

    centers = Center.objects.filter(
        doctor_time_slots__doctor=doctor,
        is_active=True
    ).distinct().order_by('name')

    centers_data = [{"id": center.id, "name": center.name} for center in centers]

    return Response({"centers": centers_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_available_dates(request):
    user_id = request.GET.get('user_id')
    center_id = request.GET.get('center_id')

    if not user_id or not center_id:
        missing = []
        if not user_id:
            missing.append('user_id')
        if not center_id:
            missing.append('center_id')
        return Response({"error": f"Missing required parameters: {', '.join(missing)}"}, status=400)

    try:
        doctor = User.objects.get(id=user_id)
        if doctor.role.name != 'DOCTOR':
            return Response({"error": "User is not a doctor"}, status=400)
    except User.DoesNotExist:
        return Response({"error": "Doctor not found"}, status=404)

    try:
        center = Center.objects.get(id=center_id, is_active=True)
    except Center.DoesNotExist:
        return Response({"error": "Center not found or inactive"}, status=404)

    dates_qs = DoctorTimeSlot.objects.filter(
        doctor=doctor,
        center=center,
        is_available=True,
        date__gte=timezone.now().date()
    ).values_list('date', flat=True).distinct().order_by('date')

    dates = [date.strftime('%Y-%m-%d') for date in dates_qs]

    return Response({"available_dates": dates})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_timeslots(request):
    user_id = request.GET.get('user_id')
    center_id = request.GET.get('center_id')
    date_str = request.GET.get('date')

    if not user_id or not center_id or not date_str:
        missing = []
        if not user_id:
            missing.append('user_id')
        if not center_id:
            missing.append('center_id')
        if not date_str:
            missing.append('date')
        return Response({"error": f"Missing required parameters: {', '.join(missing)}"}, status=400)

    try:
        doctor = User.objects.get(id=user_id)
        if doctor.role.name != 'DOCTOR':
            return Response({"error": "User is not a doctor"}, status=400)
    except User.DoesNotExist:
        return Response({"error": "Doctor not found"}, status=404)

    try:
        center = Center.objects.get(id=center_id, is_active=True)
    except Center.DoesNotExist:
        return Response({"error": "Center not found or inactive"}, status=404)

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({"error": "Invalid date format"}, status=400)

    timeslots = DoctorTimeSlot.objects.filter(
        doctor=doctor,
        center=center,
        date=date
    ).order_by('start_time')

    slots_data = [{
        'id': slot.id,
        'start_time': slot.start_time.strftime('%H:%M'),
        'end_time': slot.end_time.strftime('%H:%M'),
        'is_available': slot.is_available
    } for slot in timeslots]

    return Response({"timeslots": slots_data})


from django.shortcuts import redirect
from django.http import Http404

from django.views.generic import CreateView

class PatientConsultationDashboardView(LoginRequiredMixin, CreateView):
    model = Consultation
    form_class = ConsultationForm
    context_object_name = 'consultations'
    paginate_by = 10
    success_url = reverse_lazy('patient_consultation_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'consultation_management'):
            messages.error(request, "You don't have permission to access Consultations")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('patient_consultation_dashboard.html', self.request.user.role, 'consultation_management')]
    
    def get_queryset(self):
            queryset = Consultation.objects.select_related('patient', 'doctor').all()
            
            # Get filter parameters
            consultation_type = self.request.GET.get('consultation_type')
            status = self.request.GET.get('status')
            date_range = self.request.GET.get('date_range')
            search = self.request.GET.get('search')
            doctor = self.request.GET.get('doctor')

            # Apply consultation type filter
            if consultation_type:
                queryset = queryset.filter(consultation_type=consultation_type)

            # Apply status filter
            if status:
                queryset = queryset.filter(status=status)

            # Apply date range filter
            if date_range:
                today = timezone.now()
                if date_range == '7':
                    date_threshold = today - timedelta(days=7)
                elif date_range == '30':
                    date_threshold = today - timedelta(days=30)
                elif date_range == '90':
                    date_threshold = today - timedelta(days=90)
                queryset = queryset.filter(scheduled_datetime__gte=date_threshold)

            # Apply doctor filter
            if doctor:
                queryset = queryset.filter(doctor_id=doctor)

            # Apply search filter
            if search:
                queryset = queryset.filter(
                    Q(patient__first_name__icontains=search) |
                    Q(patient__last_name__icontains=search) |
                    Q(doctor__first_name__icontains=search) |
                    Q(doctor__last_name__icontains=search) |
                    Q(diagnosis__icontains=search) |
                    Q(chief_complaint__icontains=search)
                )

            return queryset.filter(patient=self.request.user).order_by('-scheduled_datetime')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add the patient's consultations list to context
        consultations = Consultation.objects.filter(patient=self.request.user).order_by('-scheduled_datetime')
        context['consultations'] = consultations

        # Add filter choices to context
        context.update({
            'consultation_types': ConsultationType.choices,
            'status_choices': [
                ('SCHEDULED', 'Scheduled'),
                ('IN_PROGRESS', 'In Progress'),
                ('COMPLETED', 'Completed'),
                ('CANCELLED', 'Cancelled'),
                ('NO_SHOW', 'No Show')
            ],
            'doctors': User.objects.filter(role__name='DOCTOR'),
            'current_filters': {
                'consultation_type': self.request.GET.get('consultation_type', ''),
                'status': self.request.GET.get('status', ''),
                'date_range': self.request.GET.get('date_range', ''),
                'doctor': self.request.GET.get('doctor', ''),
                'search': self.request.GET.get('search', ''),
            }
        })

        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate total consultations this month
        context['total_consultations'] = Consultation.objects.filter(
            scheduled_datetime__gte=start_of_month,
            scheduled_datetime__lte=today
        ).count()

        # Calculate upcoming follow-ups (next 7 days)
        next_week = today + timedelta(days=7)
        context['upcoming_followups'] = Consultation.objects.filter(
            follow_up_date__gte=today,
            follow_up_date__lte=next_week
        ).count()

        # Calculate average consultation duration (last 30 days)
        last_month = today - timedelta(days=30)
        completed_consultations = Consultation.objects.filter(
            status='COMPLETED',
            actual_end_time__gte=last_month
        ).exclude(actual_start_time=None)
        
        total_duration = timedelta()
        consultation_count = 0
        
        for consultation in completed_consultations:
            if consultation.actual_end_time and consultation.actual_start_time:
                duration = consultation.actual_end_time - consultation.actual_start_time
                total_duration += duration
                consultation_count += 1
        
        if consultation_count > 0:
            avg_minutes = total_duration.total_seconds() / (consultation_count * 60)
            context['avg_duration'] = round(avg_minutes)
        else:
            context['avg_duration'] = 0

        # Calculate patient satisfaction metrics from feedback
        last_month = today - timedelta(days=30)
        feedback_metrics = ConsultationFeedback.objects.filter(
            created_at__gte=last_month,
            consultation__status='COMPLETED'
        ).aggregate(
            avg_rating=Avg('rating'),
            avg_service=Avg('service_quality'),
            avg_communication=Avg('doctor_communication'),
            total_feedbacks=Count('id'),
            recommendation_rate=Avg(Cast('would_recommend', FloatField())) * 100
        )
        
        context.update({
            'patient_satisfaction': round(feedback_metrics['avg_rating'] or 0, 1),
            'total_ratings': feedback_metrics['total_feedbacks'],
            'satisfaction_metrics': {
                'service': round(feedback_metrics['avg_service'] or 0, 1),
                'communication': round(feedback_metrics['avg_communication'] or 0, 1),
                'recommendation_rate': round(feedback_metrics['recommendation_rate'] or 0)
            }
        })

        # Calculate month-over-month growth
        previous_month = start_of_month - timedelta(days=1)
        previous_month_start = previous_month.replace(day=1)
        
        current_month_count = context['total_consultations']
        previous_month_count = Consultation.objects.filter(
            scheduled_datetime__gte=previous_month_start,
            scheduled_datetime__lte=previous_month
        ).count()
        
        if previous_month_count > 0:
            context['consultation_growth'] = round(
                ((current_month_count - previous_month_count) / previous_month_count) * 100
            )
        else:
            context['consultation_growth'] = 0
            
        return context
    
class PatientsConsultationCreateView(LoginRequiredMixin, CreateView):
    model = Consultation
    form_class = ConsultationForm
    success_url = reverse_lazy('patient_consultation_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
            messages.error(request, "You don't have permission to access Consultations")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('patients_consultation_create.html', self.request.user.role, 'consultation_management')]
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['user'] = self.request.user
        except Exception as e:
            logger.error(f"Error setting form kwargs: {str(e)}")
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Dynamically set the time_slot queryset based on selected doctor and center or logged-in user
        try:
            if self.request.method == 'POST':
                doctor_id = self.request.POST.get('doctor')
                center_id = self.request.POST.get('center')
                if doctor_id and center_id:
                    form.fields['time_slot'].queryset = DoctorTimeSlot.objects.filter(
                        doctor_id=doctor_id,
                        center_id=center_id,
                        is_available=True
                    )
                else:
                    form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
            else:
                form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
        except Exception as e:
            logger.error(f"Error setting time_slot queryset in form: {str(e)}")
            form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the form instance to context explicitly
        context['form'] = self.get_form()
        return context

    def form_valid(self, form):
        logger.info(f"form_valid called by user {self.request.user.id} with role {self.request.user.role.name}")
        try:
            consultation = form.save(commit=False)
            logger.info(f"Consultation patient before assignment: {consultation.patient}")  
            logger.info(f"Logged-in user: {self.request.user} with id {self.request.user.id} and role {self.request.user.role.name}")
            
            # Validate scheduled_datetime is in the future
            if consultation.scheduled_datetime <= timezone.now():
                form.add_error('scheduled_datetime', 'Consultation must be scheduled for a future time')
                return self.form_invalid(form)
            
            # Validate doctor availability at scheduled_datetime and center
            if not self._is_doctor_available(consultation.doctor, consultation.scheduled_datetime):
                form.add_error('doctor', 'Selected doctor is not available at the scheduled time')
                return self.form_invalid(form)
            
            # Validate time_slot availability and matching center and doctor
            time_slot = consultation.time_slot
            if time_slot:
                if not time_slot.is_available:
                    form.add_error('time_slot', 'Selected time slot is not available')
                    return self.form_invalid(form)
                if time_slot.center != consultation.center:
                    form.add_error('time_slot', 'Selected time slot does not belong to the selected center')
                    return self.form_invalid(form)
                if time_slot.doctor != consultation.doctor:
                    form.add_error('time_slot', 'Selected time slot does not belong to the selected doctor')
                    return self.form_invalid(form)
            
            # Set patient from logged-in user if not set
            if not consultation.patient:
                consultation.patient = self.request.user
                logger.info(f"Assigned consultation.patient to logged-in user {self.request.user.id}")
            
            # Set priority based on urgent consultation checkbox for patients
            if self.request.user.role.name == 'PATIENT':
                if form.cleaned_data.get('urgent_consultation'):
                    consultation.priority = ConsultationPriority.HIGH
                else:
                    consultation.priority = ConsultationPriority.MEDIUM
            
            consultation.save()
            logger.info(f"Consultation saved with id {consultation.id} and patient {consultation.patient.id}")
            
            # Mark time slot as unavailable
            if time_slot:
                time_slot.is_available = False
                time_slot.save()
            
            try:
                DoctorPrivateNotes.objects.create(consultation=consultation)
            except Exception as e:
                logger.warning(f"Error creating private notes: {str(e)}")
            
            messages.success(self.request, "Consultation created successfully")
            logger.info(f"Consultation {consultation.id} created by user {self.request.user.id}")
            # Redirect to patient consultation dashboard after showing success message
            return redirect('patient_consultation_dashboard')
        except ValidationError as e:
            logger.error(f"Validation error in consultation creation: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error creating consultation: {str(e)}")
            messages.error(self.request, "An error occurred while creating the consultation")
            return self.form_invalid(form)

    def form_invalid(self, form):
        try:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(self.request, f"{field}: {error}")
            logger.warning(
                f"Invalid consultation form submission by user {self.request.user.id}: {form.errors}"
            )
            return super().form_invalid(form)
        except Exception as e:
            logger.error(f"Error handling invalid form: {str(e)}")
            messages.error(self.request, "An error occurred while processing your request")
            return redirect('patient_consultation_dashboard')

    def _is_doctor_available(self, doctor, scheduled_time):
        """Check if doctor is available at the scheduled time"""
        buffer_time = timedelta(minutes=30)  # 30 minutes before and after
        start_check = scheduled_time - buffer_time
        end_check = scheduled_time + buffer_time
        
        existing_consultations = Consultation.objects.filter(
            doctor=doctor,
            scheduled_datetime__range=(start_check, end_check),
            status__in=['SCHEDULED', 'IN_PROGRESS']
        )
        
        return not existing_consultations.exists()

    def _is_doctor_available(self, doctor, scheduled_time):
        """Check if doctor is available at the scheduled time"""
        buffer_time = timedelta(minutes=30)  # 30 minutes before and after
        start_check = scheduled_time - buffer_time
        end_check = scheduled_time + buffer_time
        
        existing_consultations = Consultation.objects.filter(
            doctor=doctor,
            scheduled_datetime__range=(start_check, end_check),
            status__in=['SCHEDULED', 'IN_PROGRESS']
        )
        
        return not existing_consultations.exists()
        
        
class ConsultationDashboardView(LoginRequiredMixin, ListView):
    model = Consultation
    context_object_name = 'consultations'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'consultation_management'):
            messages.error(request, "You don't have permission to access Consultations")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [get_template_path('consultation_dashboard.html', self.request.user.role, 'consultation_management')]

    def get_queryset(self):
        queryset = Consultation.objects.select_related('patient', 'doctor').all()

        # If user is patient, filter consultations to only their own
        if self.request.user.role.name.lower() == 'patient':
            queryset = queryset.filter(patient=self.request.user)

        # Get filter parameters
        consultation_type = self.request.GET.get('consultation_type')
        status = self.request.GET.get('status')
        date_range = self.request.GET.get('date_range')
        search = self.request.GET.get('search')
        doctor = self.request.GET.get('doctor')

        # Apply consultation type filter
        if consultation_type:
            queryset = queryset.filter(consultation_type=consultation_type)

        # Apply status filter
        if status:
            queryset = queryset.filter(status=status)

        # Apply date range filter
        if date_range:
            today = timezone.now()
            if date_range == '7':
                date_threshold = today - timedelta(days=7)
            elif date_range == '30':
                date_threshold = today - timedelta(days=30)
            elif date_range == '90':
                date_threshold = today - timedelta(days=90)
            queryset = queryset.filter(scheduled_datetime__gte=date_threshold)

        # Apply doctor filter
        if doctor:
            queryset = queryset.filter(doctor_id=doctor)

        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(doctor__first_name__icontains=search) |
                Q(doctor__last_name__icontains=search) |
                Q(diagnosis__icontains=search) |
                Q(chief_complaint__icontains=search)
            )

        return queryset.order_by('-scheduled_datetime')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter choices to context
        context.update({
            'consultation_types': ConsultationType.choices,
            'status_choices': [
                ('SCHEDULED', 'Scheduled'),
                ('IN_PROGRESS', 'In Progress'),
                ('COMPLETED', 'Completed'),
                ('CANCELLED', 'Cancelled'),
                ('NO_SHOW', 'No Show')
            ],
            'doctors': User.objects.filter(role__name='DOCTOR'),
            'current_filters': {
                'consultation_type': self.request.GET.get('consultation_type', ''),
                'status': self.request.GET.get('status', ''),
                'date_range': self.request.GET.get('date_range', ''),
                'doctor': self.request.GET.get('doctor', ''),
                'search': self.request.GET.get('search', ''),
            }
        })
        
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate total consultations this month
        context['total_consultations'] = Consultation.objects.filter(
            scheduled_datetime__gte=start_of_month,
            scheduled_datetime__lte=today
        ).count()

        # Calculate upcoming follow-ups (next 7 days)
        next_week = today + timedelta(days=7)
        context['upcoming_followups'] = Consultation.objects.filter(
            follow_up_date__gte=today,
            follow_up_date__lte=next_week
        ).count()

        # Calculate average consultation duration (last 30 days)
        last_month = today - timedelta(days=30)
        completed_consultations = Consultation.objects.filter(
            status='COMPLETED',
            actual_end_time__gte=last_month
        ).exclude(actual_start_time=None)
        
        total_duration = timedelta()
        consultation_count = 0
        
        for consultation in completed_consultations:
            if consultation.actual_end_time and consultation.actual_start_time:
                duration = consultation.actual_end_time - consultation.actual_start_time
                total_duration += duration
                consultation_count += 1
        
        if consultation_count > 0:
            avg_minutes = total_duration.total_seconds() / (consultation_count * 60)
            context['avg_duration'] = round(avg_minutes)
        else:
            context['avg_duration'] = 0

        # Calculate patient satisfaction metrics from feedback
        last_month = today - timedelta(days=30)
        feedback_metrics = ConsultationFeedback.objects.filter(
            created_at__gte=last_month,
            consultation__status='COMPLETED'
        ).aggregate(
            avg_rating=Avg('rating'),
            avg_service=Avg('service_quality'),
            avg_communication=Avg('doctor_communication'),
            total_feedbacks=Count('id'),
            recommendation_rate=Avg(Cast('would_recommend', FloatField())) * 100
        )
        
        context.update({
            'patient_satisfaction': round(feedback_metrics['avg_rating'] or 0, 1),
            'total_ratings': feedback_metrics['total_feedbacks'],
            'satisfaction_metrics': {
                'service': round(feedback_metrics['avg_service'] or 0, 1),
                'communication': round(feedback_metrics['avg_communication'] or 0, 1),
                'recommendation_rate': round(feedback_metrics['recommendation_rate'] or 0)
            }
        })

        # Calculate month-over-month growth
        previous_month = start_of_month - timedelta(days=1)
        previous_month_start = previous_month.replace(day=1)
        
        current_month_count = context['total_consultations']
        previous_month_count = Consultation.objects.filter(
            scheduled_datetime__gte=previous_month_start,
            scheduled_datetime__lte=previous_month
        ).count()
        
        if previous_month_count > 0:
            context['consultation_growth'] = round(
                ((current_month_count - previous_month_count) / previous_month_count) * 100
            )
        else:
            context['consultation_growth'] = 0
            
        return context

class ConsultationCreateView(LoginRequiredMixin, CreateView):
    model = Consultation
    form_class = ConsultationForm
    success_url = reverse_lazy('consultation_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                logger.warning(
                    f"Access denied to consultation creation for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to access Consultations")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in consultation dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def get_template_names(self):
        return [get_template_path(
            'consultation_create.html',
            self.request.user.role,
            'consultation_management'
        )]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['user'] = self.request.user
        except Exception as e:
            logger.error(f"Error setting form kwargs: {str(e)}")
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        try:
            if self.request.method == 'POST':
                doctor_id = self.request.POST.get('doctor')
                center_id = self.request.POST.get('center')
                if doctor_id and center_id:
                    form.fields['time_slot'].queryset = DoctorTimeSlot.objects.filter(
                        doctor_id=doctor_id,
                        center_id=center_id,
                        is_available=True
                    )
                else:
                    form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
            else:
                form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
        except Exception as e:
            logger.error(f"Error setting time_slot queryset in form: {str(e)}")
            form.fields['time_slot'].queryset = DoctorTimeSlot.objects.none()
        return form

    def form_valid(self, form):
        try:
            # Set defaults for required fields
            consultation = form.save(commit=False)
            
            # Respect the doctor selected in the form; do not override with logged-in user
            if not consultation.doctor:
                messages.error(self.request, "A doctor must be selected for the consultation")
                return self.form_invalid(form)
            
            # Updated datetime validation
            if consultation.scheduled_datetime <= timezone.now():
                form.add_error('scheduled_datetime', 'Consultation must be scheduled for a future time')
                return self.form_invalid(form)
            
            # Validate doctor availability at scheduled_datetime and center
            if not self._is_doctor_available(consultation.doctor, consultation.scheduled_datetime):
                form.add_error('doctor', 'Selected doctor is not available at the scheduled time')
                return self.form_invalid(form)
            
            # Save the consultation
            consultation.save()
            
            # Create private notes
            try:
                DoctorPrivateNotes.objects.create(consultation=consultation)
            except Exception as e:
                logger.warning(f"Error creating private notes: {str(e)}")
                # Continue execution as this is not critical
            
            messages.success(self.request, "Consultation created successfully")
            logger.info(f"Consultation {consultation.id} created by user {self.request.user.id}")
            
            return super().form_valid(form)
            
        except ValidationError as e:
            logger.error(f"Validation error in consultation creation: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error creating consultation: {str(e)}")
            messages.error(self.request, "An error occurred while creating the consultation")
            return self.form_invalid(form)

    def form_invalid(self, form):
        try:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(self.request, f"{field}: {error}")
            logger.warning(
                f"Invalid consultation form submission by user {self.request.user.id}: {form.errors}"
            )   
            return super().form_invalid(form)
        except Exception as e:
            logger.error(f"Error handling invalid form: {str(e)}")
            messages.error(self.request, "An error occurred while processing your request")
            return redirect('consultation_dashboard')

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context.update({
                'consultation_types': ConsultationType.choices,
                'priority_levels': ConsultationPriority.choices,
                'payment_statuses': PaymentStatus.choices,
                'page_title': 'Create New Consultation',
                'submit_text': 'Schedule Consultation'
            })
            return context
        except Exception as e:
            logger.error(f"Error getting context data: {str(e)}")
            return {'error': 'Error loading page data'}
        

class ConsultationDetailView(LoginRequiredMixin, DetailView):
    model = Consultation
    context_object_name = 'consultation'
    
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'consultation_management'):
                logger.warning(f"Access denied to consultation details for user {request.user.id}")
                messages.error(request, "You don't have permission to view consultation details")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in consultation detail dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the consultation details")
            return redirect('dashboard')

    def get_template_names(self):
        try:
            return [get_template_path(
                'consultation_detail.html',
                self.request.user.role,
                'consultation_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['consultation_management/default_consultation_detail.html']

    def get_object(self, queryset=None):
        try:
            return Consultation.objects.select_related(
                'patient',
                'doctor',
                'private_notes',
                'treatment_plan',
                'staff_instructions'
            ).prefetch_related(
                'prescriptions__items__medication',
                'phototherapy_sessions',
                'attachments'
            ).get(pk=self.kwargs['pk'])
        except Consultation.DoesNotExist:
            logger.warning(f"Consultation {self.kwargs['pk']} not found")
            raise Http404("Consultation not found")
        except Exception as e:
            logger.error(f"Error retrieving consultation: {str(e)}")
            raise

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            consultation = self.object
            
            # Base consultation information
            context['page_title'] = f'Consultation Details - {consultation.patient.get_full_name()}'
            
            # Get previous consultations
            try:
                context['previous_consultations'] = Consultation.objects.filter(
                    patient=consultation.patient,
                    scheduled_datetime__lt=consultation.scheduled_datetime
                ).order_by('-scheduled_datetime')[:5]
            except Exception as e:
                logger.warning(f"Error fetching previous consultations: {str(e)}")
                context['previous_consultations'] = []
            
            # Get prescriptions with stock information
            try:
                prescriptions = consultation.prescriptions.prefetch_related(
                    'items__medication',
                    'items__stock_item'
                ).all()
                context['prescriptions'] = prescriptions
                
                # Get previous consultations' prescriptions for templates
                previous_prescriptions = Prescription.objects.filter(
                    consultation__patient=consultation.patient,
                    consultation__scheduled_datetime__lt=consultation.scheduled_datetime
                ).prefetch_related('items__medication')[:5]
                context['previous_prescriptions'] = previous_prescriptions
                
                # Get prescription templates
                context['prescription_templates'] = PrescriptionTemplate.objects.filter(
                    Q(doctor=consultation.doctor) | Q(is_global=True)
                )
            except Exception as e:
                logger.warning(f"Error fetching prescriptions data: {str(e)}")
                context['prescriptions'] = None
                context['prescription_error'] = "Unable to load prescriptions"
            
            # Get treatment plan details with costing
            try:
                if hasattr(consultation, 'treatment_plan'):
                    context['treatment_plan_items'] = consultation.treatment_plan.items.all()
                    context['treatment_plan_cost'] = consultation.treatment_plan.total_cost
                    context['payment_status'] = consultation.treatment_plan.get_payment_status_display()
            except Exception as e:
                logger.warning(f"Error fetching treatment plan: {str(e)}")
                context['treatment_plan_items'] = None
                context['treatment_plan_error'] = "Unable to load treatment plan"
            
            # Get phototherapy sessions
            try:
                context['phototherapy_sessions'] = consultation.phototherapy_sessions.select_related(
                    'phototherapy_session'
                ).all()
            except Exception as e:
                logger.warning(f"Error fetching phototherapy sessions: {str(e)}")
                context['phototherapy_sessions'] = None
                context['phototherapy_error'] = "Unable to load phototherapy sessions"
            
            # Get consultation history timeline
            try:
                context['consultation_history'] = self._get_consultation_history(consultation)
            except Exception as e:
                logger.warning(f"Error generating consultation history: {str(e)}")
                context['consultation_history'] = None
            
            # Add permissions context
            context['can_edit'] = PermissionManager.check_module_modify(
                self.request.user, 
                'consultation_management'
            )
            context['can_delete'] = PermissionManager.check_module_delete(
                self.request.user, 
                'consultation_management'
            )
            context['is_doctor'] = self.request.user.role.name == 'DOCTOR'
            
            # Add consultation priority choices for staff instructions form
            context['consultation_priority_choices'] = ConsultationPriority.choices

            # Add all active medications for prescription creation
            context['medications'] = Medication.objects.filter(is_active=True).order_by('name')

            # Add phototherapy related context
            try:
                # Get active phototherapy plan
                active_phototherapy_plan = PhototherapyPlan.objects.filter(
                    patient=consultation.patient,
                    is_active=True,
                    end_date__gte=timezone.now().date()
                ).select_related('protocol').first()
                
                context['active_phototherapy_plan'] = active_phototherapy_plan
                
                # Get phototherapy sessions if there's an active plan
                if active_phototherapy_plan:
                    context['phototherapy_sessions'] = PhototherapySession.objects.filter(
                        plan=active_phototherapy_plan
                    ).order_by('scheduled_date', 'scheduled_time')
                else:
                    context['phototherapy_sessions'] = None
                
                # Check for previous plans
                context['has_previous_plans'] = PhototherapyPlan.objects.filter(
                    patient=consultation.patient
                ).exclude(
                    id=active_phototherapy_plan.id if active_phototherapy_plan else None
                ).exists()
                
            except Exception as e:
                logger.warning(f"Error fetching phototherapy data: {str(e)}")
                context.update({
                    'active_phototherapy_plan': None,
                    'phototherapy_sessions': None,
                    'has_previous_plans': False
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting consultation detail context: {str(e)}")
            messages.error(self.request, "Error loading consultation details")
            return {'error': 'Error loading consultation data'}

    def _get_consultation_history(self, consultation):
        """Generate a timeline of consultation events"""
        try:
            history = []
            
            # Add creation event
            history.append({
                'timestamp': consultation.created_at,
                'description': f'Consultation scheduled by {consultation.created_by.get_full_name() if consultation.created_by else "System"}'
            })
            
            # Add status changes
            if consultation.actual_start_time:
                history.append({
                    'timestamp': consultation.actual_start_time,
                    'description': 'Consultation started'
                })
            
            if consultation.actual_end_time:
                history.append({
                    'timestamp': consultation.actual_end_time,
                    'description': 'Consultation completed'
                })
            
            # Add prescription events
            for prescription in consultation.prescriptions.all():
                history.append({
                    'timestamp': prescription.created_at,
                    'description': 'Prescription added'
                })
            
            # Add treatment plan events
            if hasattr(consultation, 'treatment_plan'):
                history.append({
                    'timestamp': consultation.treatment_plan.created_at,
                    'description': 'Treatment plan created'
                })
            
            # Sort by timestamp
            history.sort(key=lambda x: x['timestamp'], reverse=True)    
            
            return history
        except Exception as e:
            logger.error(f"Error generating consultation history: {str(e)}")
            return []
        

class ConsultationDeleteView(LoginRequiredMixin, View):
    def post(self, request, consultation_id):  # Changed from pk to consultation_id
        if not PermissionManager.check_module_delete(request.user, 'consultation_management'):
            messages.error(request, "You don't have permission to delete consultations")
            return handler403(request, exception="Access Denied")

        try:
            consultation = get_object_or_404(Consultation, id=consultation_id)
            
            # Check if consultation is in the past
            if consultation.scheduled_datetime <= timezone.now(): 
                messages.error(request, "Cannot delete past consultations")
                return redirect('consultation_dashboard')
                
            consultation.delete()
            messages.success(request, "Consultation deleted successfully")
            return redirect('consultation_dashboard')
        except Exception as e:
            logger.error(f"Error deleting consultation {consultation_id}: {str(e)}")
            messages.error(request, "Error deleting consultation")
            return redirect('consultation_dashboard')

class ConsultationStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            new_status = request.POST.get('status')
            
            # Get choices from model directly
            valid_statuses = [status[0] for status in Consultation.STATUS_CHOICES]
            
            if not new_status or new_status not in valid_statuses:
                messages.error(request, "Invalid status provided")
                return redirect('consultation_detail', pk=pk)

            # Additional validation for status transitions
            current_status = consultation.status
            valid_transition = True
            
            if new_status == 'IN_PROGRESS' and current_status != 'SCHEDULED':
                valid_transition = False
            elif new_status == 'COMPLETED' and current_status != 'IN_PROGRESS':
                valid_transition = False
            elif new_status == 'CANCELLED' and current_status in ['COMPLETED', 'CANCELLED']:
                valid_transition = False

            if not valid_transition:
                messages.error(request, f"Cannot change status from {current_status} to {new_status}")
                return redirect('consultation_detail', pk=pk)

            # Update status and timestamps
            consultation.status = new_status
            if new_status == 'IN_PROGRESS':
                consultation.actual_start_time = timezone.now()
            elif new_status == 'COMPLETED':
                consultation.actual_end_time = timezone.now()

            consultation.save()
            messages.success(request, f"Consultation status updated to {consultation.get_status_display()}")
            
            return redirect('consultation_detail', pk=pk)

        except Exception as e:

            logger.error(f"Error updating consultation status: {str(e)}")
            messages.error(request, "An error occurred while updating the consultation status")
            return redirect('consultation_detail', pk=pk)
        

class StaffInstructionsUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to modify staff instructions")
                return redirect('consultation_detail', pk=pk)
            
            # Validate priority
            priority = request.POST.get('priority')
            if priority not in dict(ConsultationPriority.choices):
                messages.error(request, "Invalid priority level")
                return redirect('consultation_detail', pk=pk)
            
            # Get or create staff instructions
            staff_instructions, created = StaffInstruction.objects.get_or_create(
                consultation=consultation
            )
            
            # Update all fields
            staff_instructions.pre_consultation = request.POST.get('pre_consultation', '')
            staff_instructions.during_consultation = request.POST.get('during_consultation', '')
            staff_instructions.post_consultation = request.POST.get('post_consultation', '')
            staff_instructions.priority = priority
            
            # Save changes
            staff_instructions.save()
            
            messages.success(request, "Staff instructions updated successfully")
            logger.info(f"Staff instructions updated for consultation {pk} by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating staff instructions: {str(e)}")
            messages.error(request, "An error occurred while updating staff instructions")
        
        return redirect('consultation_detail', pk=pk)

class ClinicalInformationUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to modify clinical information")
                return redirect('consultation_detail', pk=pk)
            
            # Update vitals
            vitals = {
                'bp': request.POST.get('vitals_bp', ''),
                'temperature': request.POST.get('vitals_temp', ''),
                'pulse': request.POST.get('vitals_pulse', ''),
                'weight': request.POST.get('vitals_weight', '')
            }
            
            # Update consultation fields
            consultation.vitals = vitals
            consultation.chief_complaint = request.POST.get('chief_complaint', '')
            consultation.symptoms = request.POST.get('symptoms', '')
            consultation.clinical_notes = request.POST.get('clinical_notes', '')
            consultation.diagnosis = request.POST.get('diagnosis', '')
            
            consultation.save()
            
            messages.success(request, "Clinical information updated successfully")
            logger.info(f"Clinical information updated for consultation {pk} by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating clinical information: {str(e)}")
            messages.error(request, "An error occurred while updating clinical information")
            
        return redirect('consultation_detail', pk=pk)

class DoctorNotesUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Allow both doctors and administrators
        return self.request.user.role.name in ['DOCTOR', 'ADMINISTRATOR']

    def handle_no_permission(self):
        messages.error(self.request, "Only doctors and administrators can modify these notes")
        return redirect('consultation_detail', pk=self.kwargs['pk'])

    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            
            # Add logging for who made the changes
            logger.info(
                f"Doctor's notes update initiated by {request.user.role.name} "
                f"({request.user.get_full_name()}) for consultation {pk}"
            )
            
            # Get or create private notes
            private_notes, created = DoctorPrivateNotes.objects.get_or_create(
                consultation=consultation
            )
            
            # Update all fields
            private_notes.clinical_observations = request.POST.get('clinical_observations', '')
            private_notes.differential_diagnosis = request.POST.get('differential_diagnosis', '')
            private_notes.treatment_rationale = request.POST.get('treatment_rationale', '')
            private_notes.private_remarks = request.POST.get('private_remarks', '')
            
            private_notes.save()
            
            messages.success(request, "Doctor's notes updated successfully")
            logger.info(
                f"Doctor's notes updated for consultation {pk} by "
                f"{request.user.role.name} ({request.user.get_full_name()})"
            )
            
        except Exception as e:
            logger.error(f"Error updating doctor's notes: {str(e)}")
            messages.error(request, "An error occurred while updating the notes")
            
        return redirect('consultation_detail', pk=pk)

class PatientInstructionsUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to modify patient instructions")
                return redirect('consultation_detail', pk=pk)
            
            # Update instructions
            consultation.patient_instructions = request.POST.get('patient_instructions', '')
            consultation.lifestyle_instructions = request.POST.get('lifestyle_instructions', '')
            consultation.care_instructions = request.POST.get('care_instructions', '')
            
            consultation.save()
            
            messages.success(request, "Patient instructions updated successfully")
            logger.info(f"Patient instructions updated for consultation {pk} by user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Error updating patient instructions: {str(e)}")
            messages.error(request, "An error occurred while updating patient instructions")
            
        return redirect('consultation_detail', pk=pk)

class TreatmentPlanUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            consultation = get_object_or_404(Consultation, pk=pk)
            
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to modify treatment plan")
                return redirect('consultation_detail', pk=pk)
            
            with transaction.atomic():
                # Get or create treatment plan
                treatment_plan, created = TreatmentPlan.objects.get_or_create(
                    consultation=consultation
                )
                
                # Update basic information
                treatment_plan.description = request.POST.get('description', '')
                treatment_plan.duration_weeks = int(request.POST.get('duration_weeks', 0))
                treatment_plan.goals = request.POST.get('goals', '')
                treatment_plan.lifestyle_modifications = request.POST.get('lifestyle_modifications', '')
                treatment_plan.dietary_recommendations = request.POST.get('dietary_recommendations', '')
                treatment_plan.exercise_recommendations = request.POST.get('exercise_recommendations', '')
                
                # Calculate total cost from items
                total_cost = 0
                
                # Clear existing items to replace with new ones
                treatment_plan.items.all().delete()
                
                # Process treatment items
                item_names = request.POST.getlist('item_names[]')
                item_descriptions = request.POST.getlist('item_descriptions[]')
                item_costs = request.POST.getlist('item_costs[]')
                
                for i in range(len(item_names)):
                    if item_names[i] and item_costs[i]:  # Only create if name and cost exist
                        cost = float(item_costs[i])
                        total_cost += cost
                        TreatmentPlanItem.objects.create(
                            treatment_plan=treatment_plan,
                            name=item_names[i],
                            description=item_descriptions[i],
                            cost=cost,
                            order=i
                        )
                
                treatment_plan.total_cost = total_cost
                treatment_plan.save()
                
                messages.success(request, "Treatment plan updated successfully")
                logger.info(f"Treatment plan updated for consultation {pk} by user {request.user.id}")
                
        except ValueError as e:
            messages.error(request, "Invalid values provided for treatment plan")
            logger.error(f"Value error updating treatment plan: {str(e)}")
        except Exception as e:
            messages.error(request, "An error occurred while updating the treatment plan")
            logger.error(f"Error updating treatment plan: {str(e)}")
            
        return redirect('consultation_detail', pk=pk)

class ConsultationEditView(LoginRequiredMixin, UpdateView):
    model = Consultation
    form_class = ConsultationForm
    template_name = 'administrator/consultation_management/consultation_edit.html'
    
    def dispatch(self, request, *args, **kwargs):
        try:
            self.consultation = get_object_or_404(Consultation, pk=kwargs['pk'])
            
            # Check permissions
            if not PermissionManager.check_module_modify(request.user, 'consultation_management'):
                messages.error(request, "You don't have permission to edit consultations")
                return redirect('consultation_detail', pk=self.consultation.pk)
            
            # Prevent editing completed or cancelled consultations
            if self.consultation.status in ['COMPLETED', 'CANCELLED']:
                messages.error(request, "Cannot edit completed or cancelled consultations")
                return redirect('consultation_detail', pk=self.consultation.pk)
            
            # Prevent editing past consultations
            if self.consultation.scheduled_datetime < timezone.now():
                messages.error(request, "Cannot edit past consultations")
                return redirect('consultation_detail', pk=self.consultation.pk)
                
            return super().dispatch(request, *args, **kwargs)
            
        except Http404:
            messages.error(request, "Consultation not found")
            return redirect('consultation_dashboard')
        except Exception as e:
            logger.error(f"Error in consultation edit dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the consultation")
            return redirect('consultation_dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'consultation': self.consultation,
            'page_title': 'Edit Consultation',
            'submit_text': 'Update Consultation'
        })
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                consultation = form.save(commit=False)
                
                # Validate scheduled datetime
                if consultation.scheduled_datetime <= timezone.now():
                    form.add_error('scheduled_datetime', 'Consultation must be scheduled for a future time')
                    return self.form_invalid(form)
                
                # If doctor is changed, validate availability
                if 'doctor' in form.changed_data:
                    if not self._is_doctor_available(consultation.doctor, consultation.scheduled_datetime):
                        form.add_error('doctor', 'Selected doctor is not available at this time')
                        return self.form_invalid(form)
                
                consultation.save()
                
                messages.success(self.request, "Consultation updated successfully")
                logger.info(f"Consultation {consultation.id} updated by user {self.request.user.id}")
                
                return redirect('consultation_detail', pk=consultation.pk)
                
        except ValidationError as e:
            logger.error(f"Validation error in consultation update: {str(e)}")
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error updating consultation: {str(e)}")
            messages.error(self.request, "An error occurred while updating the consultation")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below")
        return super().form_invalid(form)

    def _is_doctor_available(self, doctor, scheduled_time):
        """Check if doctor is available at the scheduled time"""
        buffer_time = timedelta(minutes=30)  # 30 minutes before and after
        start_check = scheduled_time - buffer_time
        end_check = scheduled_time + buffer_time
        
        existing_consultations = Consultation.objects.filter(
            doctor=doctor,
            scheduled_datetime__range=(start_check, end_check),
            status__in=['SCHEDULED', 'IN_PROGRESS']
        ).exclude(pk=self.consultation.pk)
        
        return not existing_consultations.exists()

