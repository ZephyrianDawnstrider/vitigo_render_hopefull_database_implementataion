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
from ..models import ComplianceReport
from ..utils import get_template_path
from ..forms import ComplianceReportForm

# Configure logging
logger = logging.getLogger(__name__)

class ComplianceReportListView(LoginRequiredMixin, ListView):
    """View for listing compliance reports"""
    model = ComplianceReport
    context_object_name = 'reports'
    paginate_by = 10

    def get_template_names(self):
        try:
            return [get_template_path(
                'reports/report_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading report template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                return handler403(request, exception="Access denied to reports")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in report list dispatch: {str(e)}")
            return handler500(request, exception="Error accessing reports")

    def get_queryset(self):
        queryset = ComplianceReport.objects.all()
        report_type = self.request.GET.get('type')
        search = self.request.GET.get('search')

        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

class ComplianceReportDetailView(LoginRequiredMixin, DetailView):
    """View for displaying report details"""
    model = ComplianceReport
    context_object_name = 'report'

    def get_template_names(self):
        try:
            return [get_template_path(
                'reports/report_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading report detail template"
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {'name': 'Home', 'url': reverse_lazy('home')},
            {'name': 'Compliance Management', 'url': reverse_lazy('compliance_management:report_list')},
            {'name': 'Report Details'}
        ]
        return context

class ComplianceReportCreateView(LoginRequiredMixin, CreateView):
    """View for creating new reports"""
    model = ComplianceReport
    form_class = ComplianceReportForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'reports/report_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading report form template"
            )

    def get_success_url(self):
        return reverse_lazy('compliance_management:report_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.generated_by = self.request.user
        return super().form_valid(form)

class ComplianceReportUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing reports"""
    model = ComplianceReport
    form_class = ComplianceReportForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'reports/report_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading report form template"
            )

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context['is_edit'] = True
            context['report'] = self.get_object()
            return context
        except Exception as e:
            logger.error(f"Error in report edit context: {str(e)}")
            messages.error(self.request, "Error loading form data")
            return {}

    def get_success_url(self):
        return reverse_lazy('compliance_management:report_detail', kwargs={'pk': self.object.pk})

class ComplianceReportDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting reports"""
    model = ComplianceReport
    success_url = reverse_lazy('compliance_management:report_list')

    def delete(self, request, *args, **kwargs):
        try:
            report = self.get_object()
            messages.success(request, "Report deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting report: {str(e)}")
            messages.error(request, "Error deleting report")
            return handler500(request, exception="Error deleting report")