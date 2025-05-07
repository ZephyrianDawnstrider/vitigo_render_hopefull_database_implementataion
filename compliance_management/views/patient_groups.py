# Standard Library imports
import logging

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from django.db.models import Q

# Local imports
from access_control.utils import PermissionManager
from error_handling.views import handler403, handler500, handler401
from ..models import PatientGroup
from ..forms import PatientGroupForm
from ..utils import get_template_path

logger = logging.getLogger(__name__)

class PatientGroupListView(LoginRequiredMixin, ListView):
    """View for listing patient groups"""
    model = PatientGroup
    context_object_name = 'groups'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'groups/group_list.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request, 
                exception="Error loading group template"
            )

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                return handler403(request, exception="Access denied to patient groups")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in group list dispatch: {str(e)}")
            return handler500(request, exception="Error accessing patient groups")

    def get_queryset(self):
        queryset = PatientGroup.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset

class PatientGroupDetailView(LoginRequiredMixin, DetailView):
    """View for displaying patient group details"""
    model = PatientGroup
    context_object_name = 'group'

    def get_template_names(self):
        try:
            return [get_template_path(
                'groups/group_detail.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading group detail template"
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient_count'] = self.object.patients.count()
        return context

class PatientGroupCreateView(LoginRequiredMixin, CreateView):
    """View for creating new patient groups"""
    model = PatientGroup
    form_class = PatientGroupForm
    success_url = reverse_lazy('compliance_management:group_list')

    def get_template_names(self):
        try:
            return [get_template_path(
                'groups/group_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading group form template"
            )

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Patient group created successfully")
        return response

class PatientGroupUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing patient groups"""
    model = PatientGroup
    form_class = PatientGroupForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'groups/group_form.html',
                self.request.user.role,
                'compliance_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(
                self.request,
                exception="Error loading group form template"
            )

    def get_success_url(self):
        return reverse_lazy('compliance_management:group_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Patient group updated successfully")
        return response

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context['is_edit'] = True
            context['group'] = self.get_object()
            return context
        except Exception as e:
            logger.error(f"Error in group edit context: {str(e)}")
            messages.error(self.request, "Error loading form data")
            return {}

class PatientGroupDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting patient groups"""
    model = PatientGroup
    success_url = reverse_lazy('compliance_management:group_list')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return handler401(request, exception="Authentication required")
            
            if not PermissionManager.check_module_access(request.user, 'compliance_management'):
                return handler403(request, exception="Access denied to delete patient groups")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in group delete dispatch: {str(e)}")
            return handler500(request, exception="Error deleting patient group")

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Patient group deleted successfully")
            return response
        except Exception as e:
            logger.error(f"Error deleting patient group: {str(e)}")
            messages.error(request, "Error deleting patient group")
            return handler500(request, exception="Error deleting patient group")
