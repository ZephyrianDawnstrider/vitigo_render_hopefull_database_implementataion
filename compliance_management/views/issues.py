# Standard Library imports
import logging
from datetime import datetime, timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

# Local/Relative imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import ComplianceIssue
from ..forms import ComplianceIssueForm
from ..utils import get_template_path

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceIssueListView(LoginRequiredMixin, ListView):
    """View for listing compliance issues"""
    model = ComplianceIssue
    context_object_name = 'issues'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'issues/issue_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, exception="Error loading issue template")

    def get_queryset(self):
        queryset = ComplianceIssue.objects.select_related('patient', 'assigned_to')
        
        # Apply filters
        status = self.request.GET.get('status')
        severity = self.request.GET.get('severity')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if severity:
            queryset = queryset.filter(severity=severity)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context.update({
                'status_choices': ComplianceIssue.STATUS_CHOICES,
                'severity_choices': ComplianceIssue.SEVERITY_CHOICES,
                'current_filters': {
                    'status': self.request.GET.get('status', ''),
                    'severity': self.request.GET.get('severity', ''),
                    'search': self.request.GET.get('search', '')
                },
                'open_issues': self.model.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
                'high_priority': self.model.objects.filter(severity='HIGH', status__in=['OPEN', 'IN_PROGRESS']).count()
            })
            return context
        except Exception as e:
            logger.error(f"Error in issue list context: {str(e)}")
            return {}

class ComplianceIssueDetailView(LoginRequiredMixin, DetailView):
    """View for displaying issue details"""
    model = ComplianceIssue
    context_object_name = 'issue'

    def get_template_names(self):
        try:
            return [get_template_path(
                'issues/issue_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, exception="Error loading issue detail template")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            issue = self.get_object()
            context.update({
                'related_schedules': issue.patient.compliance_schedules.order_by('-scheduled_date')[:5],
                'patient_metrics': issue.patient.compliance_metrics.filter(
                    evaluation_date__gte=timezone.now().date() - timedelta(days=30)
                ).order_by('-evaluation_date').first()
            })
            return context
        except Exception as e:
            logger.error(f"Error in issue detail context: {str(e)}")
            return {}

class ComplianceIssueCreateView(LoginRequiredMixin, CreateView):
    """View for creating new issues"""
    model = ComplianceIssue
    form_class = ComplianceIssueForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'issues/issue_create.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, exception="Error loading issue form template")

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Issue created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating issue: {str(e)}")
            messages.error(self.request, "Error creating issue")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('compliance_management:issue_detail', kwargs={'pk': self.object.pk})

class ComplianceIssueUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating issues"""
    model = ComplianceIssue
    form_class = ComplianceIssueForm

    def get_template_names(self):
        try:
            return [get_template_path(
                'issues/issue_edit.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, exception="Error loading issue form template")

    def form_valid(self, form):
        try:
            # Handle resolution
            if form.instance.status in ['RESOLVED', 'CLOSED']:
                form.instance.resolved_at = timezone.now()
                form.instance.resolved_by = self.request.user

            response = super().form_valid(form)
            messages.success(self.request, "Issue updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating issue: {str(e)}")
            messages.error(self.request, "Error updating issue")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('compliance_management:issue_detail', kwargs={'pk': self.object.pk})

class ComplianceIssueDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting issues"""
    model = ComplianceIssue
    success_url = reverse_lazy('compliance_management:issue_list')

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Issue deleted successfully")
            return response
        except Exception as e:
            logger.error(f"Error deleting issue: {str(e)}")
            messages.error(request, "Error deleting issue")
            return handler500(request, exception="Error deleting issue")