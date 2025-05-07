# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
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
from ..models import ProcedureType, ProcedureCategory
from ..forms import ProcedureTypeForm
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class ProcedureTypeListView(LoginRequiredMixin, ListView):
    """View for listing procedure types"""
    model = ProcedureType
    context_object_name = 'procedure_types'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'types/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading type list template")

    def get_queryset(self):
        queryset = ProcedureType.objects.select_related('category').annotate(
            procedures_count=Count('procedures')
        )
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'active_types': self.get_queryset().filter(is_active=True).count(),
            'total_types': self.get_queryset().count(),
            'categories': ProcedureCategory.objects.all()
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to type list")
                return handler403(request, "Access denied to type list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing type list")

class ProcedureTypeDetailView(LoginRequiredMixin, DetailView):
    """View for displaying procedure type details"""
    model = ProcedureType
    context_object_name = 'procedure_type'

    def get_template_names(self):
        try:
            return [get_template_path(
                'types/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading type detail template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        procedure_type = self.get_object()
        context.update({
            'procedures': procedure_type.procedures.all()[:5],
            'procedures_count': procedure_type.procedures.count(),
            'prerequisites': procedure_type.prerequisites.all(),
            'instructions': procedure_type.instructions.all(),
            'checklist_templates': procedure_type.checklist_templates.all(),
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view type")
                return handler403(request, "Access denied to view type")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing type details")

class ProcedureTypeCreateView(LoginRequiredMixin, CreateView):
    """View for creating new procedure types"""
    model = ProcedureType
    form_class = ProcedureTypeForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'types/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading type form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Procedure type created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating procedure type: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating procedure type")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:type_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create type")
                return handler403(request, "Access denied to create type")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing type creation")

class ProcedureTypeUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating procedure types"""
    model = ProcedureType
    form_class = ProcedureTypeForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'types/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading type form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_edit': True,
            'procedure_type': self.get_object(),
            'procedures_count': self.get_object().procedures.count()
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Procedure type updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating procedure type: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating procedure type")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:type_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit type")
                return handler403(request, "Access denied to edit type")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing type edit")

class ProcedureTypeDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting procedure types"""
    model = ProcedureType
    success_url = reverse_lazy('procedure_management:type_list')

    def delete(self, request, *args, **kwargs):
        try:
            procedure_type = self.get_object()
            if procedure_type.procedures.exists():
                messages.error(request, "Cannot delete procedure type with existing procedures")
                return self.render_to_response(self.get_context_data())
            
            logger.info(f"Procedure type {procedure_type.pk} deleted by {request.user}")
            messages.success(request, "Procedure type deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting procedure type: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting procedure type")
            return handler500(request, "Error deleting procedure type")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete type")
                return handler403(request, "Access denied to delete type")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing type deletion")
