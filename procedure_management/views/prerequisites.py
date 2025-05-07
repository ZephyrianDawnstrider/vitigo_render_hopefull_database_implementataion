# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

# Third-party app imports
from access_control.utils import PermissionManager
from error_handling.views import handler401, handler403, handler500

# Local application imports
from ..models import ProcedurePrerequisite, ProcedureType
from ..forms import ProcedurePrerequisiteForm
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class PrerequisiteListView(LoginRequiredMixin, ListView):
    """View for listing procedure prerequisites"""
    model = ProcedurePrerequisite
    context_object_name = 'prerequisites'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'prerequisites/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading prerequisites list template")

    def get_queryset(self):
        queryset = ProcedurePrerequisite.objects.select_related('procedure_type')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(procedure_type__name__icontains=search_query)
            )
        
        procedure_type = self.request.GET.get('procedure_type')
        if procedure_type:
            queryset = queryset.filter(procedure_type_id=procedure_type)
        
        return queryset.order_by('procedure_type', 'order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'procedure_types': ProcedureType.objects.all(),
            'mandatory_count': self.get_queryset().filter(is_mandatory=True).count(),
            'total_count': self.get_queryset().count()
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to prerequisites list")
                return handler403(request, "Access denied to prerequisites list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing prerequisites list")

class PrerequisiteDetailView(LoginRequiredMixin, DetailView):
    """View for displaying prerequisite details"""
    model = ProcedurePrerequisite
    context_object_name = 'prerequisite'

    def get_template_names(self):
        try:
            return [get_template_path(
                'prerequisites/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading prerequisite detail template")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view prerequisite")
                return handler403(request, "Access denied to view prerequisite")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing prerequisite details")

class PrerequisiteCreateView(LoginRequiredMixin, CreateView):
    """View for creating new prerequisites"""
    model = ProcedurePrerequisite
    form_class = ProcedurePrerequisiteForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'prerequisites/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading prerequisite form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Prerequisite created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating prerequisite: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating prerequisite")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:prerequisite_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create prerequisite")
                return handler403(request, "Access denied to create prerequisite")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing prerequisite creation")

class PrerequisiteUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating prerequisites"""
    model = ProcedurePrerequisite
    form_class = ProcedurePrerequisiteForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'prerequisites/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading prerequisite form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_edit': True,
            'prerequisite': self.get_object()
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Prerequisite updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating prerequisite: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating prerequisite")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:prerequisite_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit prerequisite")
                return handler403(request, "Access denied to edit prerequisite")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing prerequisite edit")

class PrerequisiteDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting prerequisites"""
    model = ProcedurePrerequisite
    success_url = reverse_lazy('procedure_management:prerequisite_list')

    def delete(self, request, *args, **kwargs):
        try:
            prerequisite = self.get_object()
            logger.info(f"Prerequisite {prerequisite.pk} deleted by {request.user}")
            messages.success(request, "Prerequisite deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting prerequisite: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting prerequisite")
            return handler500(request, "Error deleting prerequisite")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete prerequisite")
                return handler403(request, "Access denied to delete prerequisite")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing prerequisite deletion")
