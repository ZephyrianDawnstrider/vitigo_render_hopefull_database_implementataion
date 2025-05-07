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
from ..models import ProcedureChecklistTemplate, ChecklistItem
from ..forms import ProcedureChecklistTemplateForm
from ..utils import get_template_path

# Configure logging
logger = logging.getLogger(__name__)

class ChecklistTemplateListView(LoginRequiredMixin, ListView):
    """View for listing checklist templates"""
    model = ProcedureChecklistTemplate
    context_object_name = 'templates'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklist_templates/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading template list")

    def get_queryset(self):
        queryset = ProcedureChecklistTemplate.objects.select_related('procedure_type')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(procedure_type__name__icontains=search_query)
            )
        
        return queryset.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_templates'] = self.get_queryset().count()
        context['active_templates'] = self.get_queryset().filter(is_active=True).count()
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to template list")
                return handler403(request, "Access denied to template list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing template list")

class ChecklistTemplateDetailView(LoginRequiredMixin, DetailView):
    """View for displaying template details"""
    model = ProcedureChecklistTemplate
    context_object_name = 'template'
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklist_templates/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading template detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.order_by('order')
        context['checklists_count'] = self.object.procedurechecklist_set.count()
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to template detail")
                return handler403(request, "Access denied to template detail")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing template detail")

class ChecklistTemplateCreateView(LoginRequiredMixin, CreateView):
    """View for creating new checklist templates"""
    model = ProcedureChecklistTemplate
    form_class = ProcedureChecklistTemplateForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklist_templates/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading template form")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Checklist template created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating checklist template")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:template_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create template")
                return handler403(request, "Access denied to create template")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing template creation")

class ChecklistTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating checklist templates"""
    model = ProcedureChecklistTemplate
    form_class = ProcedureChecklistTemplateForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklist_templates/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading template form")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_edit': True,
            'items': self.object.items.order_by('order')
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Checklist template updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating template: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating checklist template")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:template_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit template")
                return handler403(request, "Access denied to edit template")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing template edit")

class ChecklistTemplateDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting checklist templates"""
    model = ProcedureChecklistTemplate
    success_url = reverse_lazy('procedure_management:template_list')

    def delete(self, request, *args, **kwargs):
        try:
            template = self.get_object()
            if template.procedurechecklist_set.exists():
                messages.error(request, "Cannot delete template with existing checklists")
                return handler403(request, "Template has associated checklists")
            
            # Delete all associated items first
            template.items.all().delete()
            messages.success(request, "Checklist template deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting checklist template")
            return handler500(request, "Error deleting template")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete template")
                return handler403(request, "Access denied to delete template")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing template deletion")
