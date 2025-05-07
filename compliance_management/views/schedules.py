# Standard Library imports
import logging
from datetime import datetime, timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy

# Local/Relative imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import ComplianceSchedule
from ..utils import get_template_path
from ..forms import ComplianceScheduleForm

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceScheduleListView(LoginRequiredMixin, ListView):
    """View for listing and managing compliance schedules"""
    model = ComplianceSchedule
    context_object_name = 'schedules'
    paginate_by = 10

    def get_template_names(self):
        """Dynamically get template based on user role"""
        try:
            return [get_template_path(
                'schedules/schedule_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading schedule template"
            )

    def dispatch(self, request, *args, **kwargs):
        """Handle request dispatch with proper authentication and permissions"""
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(f"Access denied for user {request.user} to compliance schedules")
                return handler403(request, exception="Access denied to compliance schedules")

            # Audit logging
            logger.info(f"Schedule list accessed by {request.user} at {timezone.now()}")
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in schedule list dispatch: {str(e)}", exc_info=True)
            return handler500(request, exception="Error accessing schedules")

    def get_queryset(self):
        """Get filtered queryset based on search and filter parameters"""
        try:
            queryset = ComplianceSchedule.objects.select_related(
                'patient', 
                'assigned_to'
            ).all()

            # Apply filters from request
            filters = self.get_filter_params()
            
            if filters['status']:
                queryset = queryset.filter(status=filters['status'])
            
            if filters['priority']:
                queryset = queryset.filter(priority=filters['priority'])
            
            if filters['date_from']:
                try:
                    date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                    queryset = queryset.filter(scheduled_date=date_from)
                except ValueError:
                    logger.warning("Invalid date format provided in filter")
            
            if filters['search']:
                queryset = queryset.filter(
                    Q(patient__first_name__icontains=filters['search']) |
                    Q(patient__last_name__icontains=filters['search']) |
                    Q(schedule_notes__icontains=filters['search'])
                )

            return queryset.order_by('scheduled_date', 'scheduled_time')

        except Exception as e:
            logger.error(f"Error in schedule queryset: {str(e)}", exc_info=True)
            messages.error(self.request, "Error retrieving schedules")
            return ComplianceSchedule.objects.none()

    def get_filter_params(self):
        """Extract and validate filter parameters from request"""
        return {
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'search': self.request.GET.get('search', ''),
        }

    def get_context_data(self, **kwargs):
        """Prepare context data for template rendering"""
        if not self.request.user.is_authenticated:
            return handler401(self.request, exception="Authentication required")

        try:
            context = super().get_context_data(**kwargs)
            
            context.update({
                'status_choices': ComplianceSchedule.STATUS_CHOICES,
                'priority_choices': ComplianceSchedule.PRIORITY_CHOICES,
                'current_filters': self.get_filter_params(),
                'total_schedules': self.get_queryset().count(),
                'completed_schedules': self.get_queryset().filter(status='COMPLETED').count(),
                'pending_schedules': self.get_queryset().filter(
                    status__in=['SCHEDULED', 'IN_PROGRESS']
                ).count(),
                'overdue_schedules': self.get_queryset().filter(
                    scheduled_date__lt=timezone.now().date(),
                    status__in=['SCHEDULED', 'IN_PROGRESS']
                ).count(),
                'today': timezone.now().date(),
                'date_range': {
                    'start': (timezone.now() - timedelta(days=30)).date(),
                    'end': (timezone.now() + timedelta(days=30)).date(),
                }
            })
            
            return context

        except Exception as e:
            logger.error(f"Error in schedule context data: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading page data")
            return {}

    def handle_no_permission(self):
        """Handle unauthorized access attempts"""
        return handler403(
            self.request, 
            exception="You don't have permission to view schedules"
        )

class ComplianceScheduleDetailView(LoginRequiredMixin, DetailView):
    """View for displaying detailed information about a compliance schedule"""
    model = ComplianceSchedule
    context_object_name = 'schedule'

    def get_template_names(self):
        try:
            return [get_template_path(
                'schedules/schedule_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading schedule detail template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(f"Access denied for user {request.user} to schedule details")
                return handler403(request, exception="Access denied to schedule details")

            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in schedule detail dispatch: {str(e)}", exc_info=True)
            return handler500(request, exception="Error accessing schedule details")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            schedule = self.get_object()
            
            # Get related data
            context.update({
                'notes': schedule.notes.select_related('created_by').order_by('-created_at'),
                'compliance_metrics': schedule.patient.compliance_metrics.filter(
                    evaluation_date=schedule.scheduled_date
                ).first(),
                'previous_schedules': ComplianceSchedule.objects.filter(
                    patient=schedule.patient,
                    scheduled_date__lt=schedule.scheduled_date
                ).order_by('-scheduled_date')[:3],
                'upcoming_schedules': ComplianceSchedule.objects.filter(
                    patient=schedule.patient,
                    scheduled_date__gt=schedule.scheduled_date
                ).order_by('scheduled_date')[:3],
                'related_issues': schedule.patient.compliance_issues.filter(
                    status__in=['OPEN', 'IN_PROGRESS']
                ).order_by('-created_at'),
            })
            
            return context
            
        except Exception as e:
            logger.error(f"Error in schedule detail context: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading schedule details")
            return {}

class ComplianceScheduleUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing compliance schedules"""
    model = ComplianceSchedule
    form_class = ComplianceScheduleForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'schedules/schedule_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading schedule form template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied for user {request.user.email} (ID: {request.user.id}) "
                    f"to edit schedule {kwargs.get('pk')}"
                )
                return handler403(request, exception="Access denied to edit schedule")

            # Enhanced audit logging
            logger.info(
                f"Schedule edit accessed by {request.user.get_full_name()} "
                f"(Email: {request.user.email}, ID: {request.user.id}, Role: {request.user.role}) "
                f"for schedule {kwargs.get('pk')} "
                f"at {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in schedule edit dispatch: {str(e)} "
                f"[User: {request.user.email}, Schedule: {kwargs.get('pk')}]", 
                exc_info=True
            )
            return handler500(request, exception="Error accessing schedule edit")

    def get_success_url(self):
        return reverse_lazy('compliance_management:schedule_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            logger.info(
                f"Schedule {self.object.pk} successfully updated by {self.request.user.get_full_name()} "
                f"(Email: {self.request.user.email}, ID: {self.request.user.id}) "
                f"at {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            messages.success(self.request, "Schedule updated successfully")
            return response
        except Exception as e:
            logger.error(
                f"Error updating schedule {self.object.pk}: {str(e)} "
                f"[User: {self.request.user.email}]",
                exc_info=True
            )
            messages.error(self.request, "Error updating schedule")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context['is_edit'] = True
            context['schedule'] = self.get_object()
            return context
        except Exception as e:
            logger.error(f"Error in schedule edit context: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading form data")
            return {}

class ComplianceScheduleDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting compliance schedules"""
    model = ComplianceSchedule
    success_url = reverse_lazy('compliance_management:schedule_list')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                logger.warning(
                    f"Access denied for user {request.user.email} (ID: {request.user.id}) "
                    f"to delete schedule {kwargs.get('pk')}"
                )
                return handler403(request, exception="Access denied to delete schedule")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in schedule delete dispatch: {str(e)} "
                f"[User: {request.user.email}, Schedule: {kwargs.get('pk')}]",
                exc_info=True
            )
            return handler500(request, exception="Error accessing schedule delete")

    def delete(self, request, *args, **kwargs):
        try:
            schedule = self.get_object()
            logger.info(
                f"Schedule {schedule.pk} deleted by {request.user.get_full_name()} "
                f"(Email: {request.user.email}, ID: {request.user.id}) "
                f"at {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            messages.success(request, "Schedule deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting schedule: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting schedule")
            return handler500(request, exception="Error deleting schedule")
