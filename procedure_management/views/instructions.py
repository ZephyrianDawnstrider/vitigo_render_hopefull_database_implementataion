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
from ..models import ProcedureInstruction, ProcedureType
from ..forms import ProcedureInstructionForm
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class InstructionListView(LoginRequiredMixin, ListView):
    """View for listing procedure instructions"""
    model = ProcedureInstruction
    context_object_name = 'instructions'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'instructions/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading instructions list template")

    def get_queryset(self):
        queryset = ProcedureInstruction.objects.select_related('procedure_type')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(procedure_type__name__icontains=search_query)
            )
        
        procedure_type = self.request.GET.get('procedure_type')
        if procedure_type:
            queryset = queryset.filter(procedure_type_id=procedure_type)
            
        instruction_type = self.request.GET.get('instruction_type')
        if instruction_type:
            queryset = queryset.filter(instruction_type=instruction_type)
        
        return queryset.order_by('procedure_type', 'instruction_type', 'order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'procedure_types': ProcedureType.objects.all(),
            'instruction_types': dict(ProcedureInstruction.INSTRUCTION_TYPE),
            'pre_count': self.get_queryset().filter(instruction_type='PRE').count(),
            'post_count': self.get_queryset().filter(instruction_type='POST').count(),
            'total_count': self.get_queryset().count()
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to instructions list")
                return handler403(request, "Access denied to instructions list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing instructions list")

class InstructionDetailView(LoginRequiredMixin, DetailView):
    """View for displaying instruction details"""
    model = ProcedureInstruction
    context_object_name = 'instruction'
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'instructions/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading instruction detail template")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view instruction")
                return handler403(request, "Access denied to view instruction")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing instruction details")

class InstructionCreateView(LoginRequiredMixin, CreateView):
    """View for creating new instructions"""
    model = ProcedureInstruction
    form_class = ProcedureInstructionForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'instructions/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading instruction form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Instruction created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating instruction: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating instruction")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:instruction_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create instruction")
                return handler403(request, "Access denied to create instruction")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing instruction creation")

class InstructionUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating instructions"""
    model = ProcedureInstruction
    form_class = ProcedureInstructionForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'instructions/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading instruction form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_edit': True,
            'instruction': self.get_object()
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Instruction updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating instruction: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating instruction")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:instruction_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit instruction")
                return handler403(request, "Access denied to edit instruction")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing instruction edit")

class InstructionDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting instructions"""
    model = ProcedureInstruction
    success_url = reverse_lazy('procedure_management:instruction_list')

    def delete(self, request, *args, **kwargs):
        try:
            instruction = self.get_object()
            logger.info(f"Instruction {instruction.pk} deleted by {request.user}")
            messages.success(request, "Instruction deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting instruction: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting instruction")
            return handler500(request, "Error deleting instruction")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete instruction")
                return handler403(request, "Access denied to delete instruction")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing instruction deletion")
