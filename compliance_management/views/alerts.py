# Standard Library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView

# Local/Relative imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import ComplianceAlert
from ..utils import get_template_path
from ..forms import ComplianceAlertForm

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceAlertListView(LoginRequiredMixin, ListView):
    """View for listing compliance alerts"""
    model = ComplianceAlert
    context_object_name = 'alerts'
    paginate_by = 10

    def get_template_names(self):
        try:
            return [get_template_path(
                'alerts/alert_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading alert template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                return handler403(request, exception="Access denied to alerts")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in alert list dispatch: {str(e)}")
            return handler500(request, exception="Error accessing alerts")

    def get_queryset(self):
        queryset = ComplianceAlert.objects.select_related('patient').all()
        severity = self.request.GET.get('severity')
        alert_type = self.request.GET.get('type')
        is_resolved = self.request.GET.get('resolved')
        search = self.request.GET.get('search')

        if severity:
            queryset = queryset.filter(severity=severity)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved == 'true')
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(message__icontains=search)
            )

        return queryset

class ComplianceAlertDetailView(LoginRequiredMixin, DetailView):
    """View for displaying alert details"""
    model = ComplianceAlert
    context_object_name = 'alert'

    def get_template_names(self):
        try:
            return [get_template_path(
                'alerts/alert_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading alert detail template"
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': reverse_lazy('home')},
            {'name': 'Compliance Management', 'url': reverse_lazy('compliance_management:alert_list')},
            {'name': 'Alert Details'}
        ]
        return context

class ComplianceAlertCreateView(LoginRequiredMixin, CreateView):
    """View for creating new alerts"""
    model = ComplianceAlert
    form_class = ComplianceAlertForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'alerts/alert_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading alert form template"
            )

    def get_success_url(self):
        return reverse_lazy('compliance_management:alert_detail', kwargs={'pk': self.object.pk})

class ComplianceAlertUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing alerts"""
    model = ComplianceAlert
    form_class = ComplianceAlertForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'alerts/alert_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading alert form template"
            )

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context['is_edit'] = True
            context['alert'] = self.get_object()
            return context
        except Exception as e:
            logger.error(f"Error in alert edit context: {str(e)}")
            messages.error(self.request, "Error loading form data")
            return {}

    def get_success_url(self):
        return reverse_lazy('compliance_management:alert_detail', kwargs={'pk': self.object.pk})

class ComplianceAlertDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting alerts"""
    model = ComplianceAlert
    success_url = reverse_lazy('compliance_management:alert_list')

    def delete(self, request, *args, **kwargs):
        try:
            alert = self.get_object()
            messages.success(request, "Alert deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting alert: {str(e)}")
            messages.error(request, "Error deleting alert")
            return handler500(request, exception="Error deleting alert")
