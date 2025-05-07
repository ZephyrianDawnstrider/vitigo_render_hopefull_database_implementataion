# Standard Library imports
import logging
from datetime import datetime, timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model

# Local/Relative imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import ComplianceReminder
from ..utils import get_template_path
from ..forms import ComplianceReminderForm

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceReminderListView(LoginRequiredMixin, ListView):
    """View for listing compliance reminders"""
    model = ComplianceReminder
    context_object_name = 'reminders'
    paginate_by = 10

    def get_template_names(self):
        try:
            return [get_template_path(
                'reminders/reminder_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading reminder template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                return handler403(request, exception="Access denied to reminders")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in reminder list dispatch: {str(e)}")
            return handler500(request, exception="Error accessing reminders")

    def get_queryset(self):
        queryset = ComplianceReminder.objects.select_related('patient').all()
        status = self.request.GET.get('status')
        reminder_type = self.request.GET.get('type')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if reminder_type:
            queryset = queryset.filter(reminder_type=reminder_type)
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(message__icontains=search)
            )

        return queryset

class ComplianceReminderDetailView(LoginRequiredMixin, DetailView):
    """View for displaying reminder details"""
    model = ComplianceReminder
    context_object_name = 'reminder'

    def get_template_names(self):
        try:
            return [get_template_path(
                'reminders/reminder_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading reminder detail template"
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': reverse_lazy('home')},
            {'name': 'Compliance Management', 'url': reverse_lazy('compliance_management:reminder_list')},
            {'name': 'Reminder Details'}
        ]
        context['action_buttons'] = {
            'edit_url': reverse_lazy('compliance_management:reminder_update', kwargs={'pk': self.object.pk}),
            'delete_url': reverse_lazy('compliance_management:reminder_delete', kwargs={'pk': self.object.pk})
        }
        return context

class ComplianceReminderCreateView(LoginRequiredMixin, CreateView):
    """View for creating new reminders"""
    model = ComplianceReminder
    form_class = ComplianceReminderForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'reminders/reminder_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading reminder form template"
            )

    def get_success_url(self):
        return reverse_lazy('compliance_management:reminder_detail', kwargs={'pk': self.object.pk})

class ComplianceReminderUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing reminders"""
    model = ComplianceReminder
    form_class = ComplianceReminderForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'reminders/reminder_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading reminder form template"
            )

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context['is_edit'] = True
            context['reminder'] = self.get_object()
            return context
        except Exception as e:
            logger.error(f"Error in reminder edit context: {str(e)}")
            messages.error(self.request, "Error loading form data")
            return {}

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Reminder updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating reminder: {str(e)}")
            messages.error(self.request, "Error updating reminder")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('compliance_management:reminder_detail', kwargs={'pk': self.object.pk})

class ComplianceReminderDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting reminders"""
    model = ComplianceReminder
    success_url = reverse_lazy('compliance_management:reminder_list')

    def delete(self, request, *args, **kwargs):
        try:
            reminder = self.get_object()
            messages.success(request, "Reminder deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting reminder: {str(e)}")
            messages.error(request, "Error deleting reminder")
            return handler500(request, exception="Error deleting reminder")

class ReminderHistoryView(LoginRequiredMixin, ListView):
    """View for displaying reminder history for a patient"""
    model = ComplianceReminder
    template_name = 'administrator/compliance_management/reminders/reminder_history.html'
    context_object_name = 'reminders'
    paginate_by = 10

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return ComplianceReminder.objects.filter(
            patient_id=patient_id
        ).select_related('patient').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = get_user_model().objects.get(id=self.kwargs.get('patient_id'))
        context.update({
            'patient': patient,
            'reminder_stats': {
                'total': self.get_queryset().count(),
                'sent': self.get_queryset().filter(status='SENT').count(),
                'failed': self.get_queryset().filter(status='FAILED').count(),
                'pending': self.get_queryset().filter(status='PENDING').count(),
            }
        })
        return context