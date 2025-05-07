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
from ..models import ProcedureChecklist, ProcedureChecklistTemplate, CompletedChecklistItem
from ..forms import ProcedureChecklistForm
from ..utils import get_template_path

# Configure logging
logger = logging.getLogger(__name__)

class ChecklistListView(LoginRequiredMixin, ListView):
    """View for listing procedure checklists"""
    model = ProcedureChecklist
    context_object_name = 'checklists'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklists/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading checklist list template")

    def get_queryset(self):
        queryset = ProcedureChecklist.objects.select_related(
            'procedure', 'template', 'completed_by'
        )
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(procedure__procedure_type__name__icontains=search_query) |
                Q(template__name__icontains=search_query) |
                Q(notes__icontains=search_query)
            )
        
        return queryset.order_by('-completed_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = ProcedureChecklistTemplate.objects.filter(is_active=True)
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to checklist list")
                return handler403(request, "Access denied to checklist list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing checklist list")

class ChecklistDetailView(LoginRequiredMixin, DetailView):
    """View for displaying checklist details"""
    model = ProcedureChecklist
    context_object_name = 'checklist'
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklists/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading checklist detail template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['completed_items'] = self.object.completed_items.select_related('item', 'completed_by')
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            checklist = self.get_object()
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to checklist details")
                return handler403(request, "Access denied to checklist details")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing checklist details")

class ChecklistCreateView(LoginRequiredMixin, CreateView):
    """View for creating new checklists"""
    model = ProcedureChecklist
    form_class = ProcedureChecklistForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklists/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading checklist form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            form.instance.completed_by = self.request.user
            response = super().form_valid(form)
            
            # Create completed items for each template item
            template_items = form.instance.template.items.all()
            for item in template_items:
                CompletedChecklistItem.objects.create(
                    checklist=form.instance,
                    item=item
                )
            
            messages.success(self.request, "Checklist created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating checklist: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating checklist")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:checklist_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create checklist")
                return handler403(request, "Access denied to create checklist")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing checklist creation")

class ChecklistUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating checklist details"""
    model = ProcedureChecklist
    form_class = ProcedureChecklistForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'checklists/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading checklist form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['completed_items'] = self.object.completed_items.select_related('item', 'completed_by')
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Checklist updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating checklist: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating checklist")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:checklist_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit checklist")
                return handler403(request, "Access denied to edit checklist")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing checklist edit")

class ChecklistDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting checklists"""
    model = ProcedureChecklist
    success_url = reverse_lazy('procedure_management:checklist_list')

    def delete(self, request, *args, **kwargs):
        try:
            checklist = self.get_object()
            # First delete all completed items
            checklist.completed_items.all().delete()
            messages.success(request, "Checklist deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting checklist: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting checklist")
            return handler500(request, "Error deleting checklist")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete checklist")
                return handler403(request, "Access denied to delete checklist")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing checklist deletion")
