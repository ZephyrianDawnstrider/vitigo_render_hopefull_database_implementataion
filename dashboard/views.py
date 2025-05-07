# Standard library imports
import logging
from datetime import timedelta
from decimal import Decimal

# Django core imports
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F, Count, Sum, Q, Avg
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.http import JsonResponse

# Local application imports
from error_handling.views import handler403, handler404, handler500
from access_control.permissions import PermissionManager
from .utils import get_template_path, get_safe_division, get_percentage_change, get_date_range_filter, cache_dashboard_data
from .exceptions import DataFetchError, StatsComputationError
from appointment_management.models import Appointment
from phototherapy_management.models import PhototherapySession
from query_management.models import Query
from procedure_management.models import Procedure
from user_management.models import CustomUser

# Get custom user model
User = get_user_model()

# Configure logging
logger = logging.getLogger(__name__)

class DashboardView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'dashboard'):
            messages.error(request, "You don't have permission to access the dashboard")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_greeting(self):
        """Return appropriate greeting based on time of day"""
        hour = timezone.now().hour
        if hour < 12:
            return "Good Morning"
        elif hour < 17:
            return "Good Afternoon"
        else:
            return "Good Evening"

    def get_dashboard_metrics(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        try:
            # Get base metrics
            today_appointments = Appointment.objects.filter(date=today)
            yesterday_appointments = Appointment.objects.filter(date=yesterday)
            
            # Calculate percentage change in appointments
            today_count = today_appointments.count()
            yesterday_count = yesterday_appointments.count()
            appointment_change = get_percentage_change(today_count, yesterday_count)

            # Get active treatments
            active_treatments = (
                PhototherapySession.objects.filter(status='IN_PROGRESS').count() +
                Procedure.objects.filter(status='IN_PROGRESS').count()
            )

            # Calculate treatment completion rate
            completed_treatments = (
                PhototherapySession.objects.filter(status='COMPLETED').count() +
                Procedure.objects.filter(status='COMPLETED').count()
            )
            total_treatments = (
                PhototherapySession.objects.count() +
                Procedure.objects.count()
            )
            completion_rate = get_safe_division(completed_treatments, total_treatments) * 100

            # Get urgent matters
            urgent_matters = (
                Query.objects.filter(priority='A', status__in=['NEW', 'IN_PROGRESS']).count() +
                Appointment.objects.filter(priority='A', status='PENDING').count()
            )

            # Get recent activities
            recent_activities = self.get_recent_activities()

            metrics = {
                'appointments': {
                    'today': today_count,
                    'completed': today_appointments.filter(status='COMPLETED').count(),
                    'change': appointment_change,
                },
                'checkins': {
                    'today': today_appointments.filter(status='CONFIRMED').count(),
                    'pending': today_appointments.filter(status__in=['SCHEDULED', 'PENDING']).count(),
                },
                'active_treatments': active_treatments,
                'treatment_completion_rate': round(completion_rate, 1),
                'treatment_success_rate': 85,  # You might want to calculate this based on your criteria
                'urgent_matters': urgent_matters,
                'queries': {
                    'total': Query.objects.filter(created_at__date=today).count(),
                    'resolved': Query.objects.filter(
                        created_at__date=today,
                        status='RESOLVED'
                    ).count(),
                },
                'recent_activities': recent_activities,
                'last_updated': timezone.now(),
            }
        except Exception as e:
            logger.error(f"Error fetching dashboard metrics: {str(e)}")
            raise DataFetchError("Failed to fetch dashboard metrics.")
        metrics = {
                # ... default values for metrics ...
            }
            
        return metrics

    def get_recent_activities(self):
        """Get recent system activities with icons"""
        activities = []
        try:
            # Get recent appointments
            recent_appointments = Appointment.objects.select_related('patient').order_by('-created_at')[:5]
            for appointment in recent_appointments:
                activities.append({
                    'type': 'APPOINTMENT',
                    'icon': 'calendar-check',
                    'description': f"New appointment scheduled for {appointment.patient.get_full_name()}",
                    'time': appointment.created_at
                })

            # Get recent queries
            recent_queries = Query.objects.select_related('user').order_by('-created_at')[:5]
            for query in recent_queries:
                activities.append({
                    'type': 'QUERY',
                    'icon': 'question-circle',
                    'description': f"New query: {query.subject}",
                    'time': query.created_at
                })

            # Sort by time
            activities.sort(key=lambda x: x['time'], reverse=True)
            return activities[:10]
        except Exception as e:
            logger.error(f"Error fetching recent activities: {str(e)}")
            return []  # Return an empty list on error

    def get_dashboard_context(self, request):
        try:
            context = {
                'greeting': self.get_greeting(),
                'current_datetime': timezone.now(),
                'metrics': self.get_dashboard_metrics(),
                'page_title': 'Dashboard',
                'module_name': 'dashboard',
            }
            # Add patient-specific data only if user is patient
            role = getattr(request.user, 'role', None)
            if role and role.name.lower() == 'patient':
                # Fetch patient profile
                patient_profile = getattr(request.user, 'patientprofile', None)
                # Fetch appointments and consultations for the patient
                appointments = Appointment.objects.filter(patient=request.user).order_by('-date', '-time_slot__start_time')
                consultations = []
                try:
                    from consultation_management.models import Consultation
                    consultations = Consultation.objects.filter(patient=request.user).order_by('-scheduled_datetime')
                except ImportError:
                    logger.warning("Consultation model not found.")
                # Fetch treatment progress data (dummy example, replace with real logic)
                treatment_progress = 75  # Placeholder percentage
                # Add to context
                context.update({
                    'user': request.user,
                    'patient_profile': patient_profile,
                    'appointments': appointments,
                    'consultations': consultations,
                    'treatment_progress': treatment_progress,
                    # For treatment progress chart data placeholders
                    'treatment_months': [],
                    'treatment_progress_data': [],
                })
            return context
        except Exception as e:
            logger.error(f"Error preparing dashboard context: {str(e)}")
            raise StatsComputationError("Failed to prepare dashboard context.")

    def get(self, request, *args, **kwargs):
        try:
            context = self.get_dashboard_context(request)
            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            messages.error(request, "Error loading dashboard data")
            return handler500(request)

    def get_template_name(self):
        role = self.request.user.role
        if role and role.name.lower() == 'patient':
            return 'patient/dashboard.html'
        return get_template_path('dashboard.html', role, 'dashboard')
