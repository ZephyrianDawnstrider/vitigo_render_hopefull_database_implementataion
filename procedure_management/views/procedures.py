# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
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
from ..forms import ProcedureForm
from ..models import Procedure, ProcedureCategory, ProcedureType
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class ProcedureListView(LoginRequiredMixin, ListView):
    model = Procedure
    context_object_name = 'procedures'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'procedures/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading procedure list template")

    def get_queryset(self):
        queryset = Procedure.objects.select_related(
            'procedure_type',
            'patient',
            'primary_doctor',
            'appointment'
        ).order_by('-scheduled_date', '-scheduled_time')

        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(procedure_type__name__icontains=search_query) |
                Q(patient__first_name__icontains=search_query) |
                Q(patient__last_name__icontains=search_query) |
                Q(primary_doctor__first_name__icontains=search_query) |
                Q(primary_doctor__last_name__icontains=search_query) |
                Q(status__icontains=search_query)
            )

        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status.upper())

        # Date range filter
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(scheduled_date__range=[start_date, end_date])

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Add filters data
            context.update({
                'procedure_types': ProcedureType.objects.all(),
                'procedure_categories': ProcedureCategory.objects.all(),
                'status_choices': Procedure.STATUS_CHOICES,
                'current_filters': {
                    'search': self.request.GET.get('search', ''),
                    'status': self.request.GET.get('status', ''),
                    'start_date': self.request.GET.get('start_date', ''),
                    'end_date': self.request.GET.get('end_date', ''),
                },
                'total_procedures': self.get_queryset().count(),
                'today_procedures': self.get_queryset().filter(
                    scheduled_date=timezone.now().date()
                ).count(),
            })
        except Exception as e:
            logger.error(f"Context data error: {str(e)}")
            context['error_message'] = "Error loading procedure data"

        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to procedure list")
                return handler403(request, "Access denied to procedure list")

            request.session['last_procedure_action'] = 'view_procedure_list'
            request.session['procedure_access_time'] = timezone.now().isoformat()
            
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure list")

class ProcedureDetailView(LoginRequiredMixin, DetailView):
    """View for displaying detailed information about a procedure"""
    model = Procedure
    context_object_name = 'procedure'

    def get_template_names(self):
        try:
            return [get_template_path(
                'procedures/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading procedure detail template")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            procedure = self.get_object()
            
            # Get consent form safely
            try:
                consent_form = procedure.consent_form
            except Procedure.consent_form.RelatedObjectDoesNotExist:
                consent_form = None

            # Get checklists safely
            checklists = procedure.checklists.all() if hasattr(procedure, 'checklists') else []
            
            # Get media files safely
            media_files = procedure.media_files.all() if hasattr(procedure, 'media_files') else []

            # Get prerequisites safely
            prerequisites = (
                procedure.procedure_type.prerequisites.all() 
                if hasattr(procedure.procedure_type, 'prerequisites') 
                else []
            )

            # Get instructions safely
            instructions = (
                procedure.procedure_type.instructions.all()
                if hasattr(procedure.procedure_type, 'instructions')
                else []
            )

            context.update({
                'consent_form': consent_form,
                'checklists': checklists,
                'media_files': media_files,
                'prerequisites': prerequisites,
                'instructions': instructions,
            })
            return context
        except Exception as e:
            logger.error(f"Error in procedure detail context: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading procedure details")
            return {
                'procedure': procedure,
                'consent_form': None,
                'checklists': [],
                'media_files': [],
                'prerequisites': [],
                'instructions': [],
                'error_message': "Some data could not be loaded"
            }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view procedure")
                return handler403(request, "Access denied to view procedure")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure details")

class ProcedureCreateView(LoginRequiredMixin, CreateView):
    """View for creating new procedures"""
    model = Procedure
    form_class = ProcedureForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'procedures/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading procedure form template")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context.update({
                'is_create': True,
                'procedure_types': ProcedureType.objects.all(),
                'title': 'Create New Procedure'
            })
            return context
        except Exception as e:
            logger.error(f"Error in procedure create context: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading form")
            return {}

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Procedure created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating procedure: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating procedure")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:procedure_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create procedure")
                return handler403(request, "Access denied to create procedure")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure creation")

class ProcedureUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing procedures"""
    model = Procedure
    form_class = ProcedureForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'procedures/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading procedure form template")

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            context.update({
                'is_edit': True,
                'procedure': self.get_object(),
                'title': 'Edit Procedure'
            })
            return context
        except Exception as e:
            logger.error(f"Error in procedure update context: {str(e)}", exc_info=True)
            messages.error(self.request, "Error loading form")
            return {}

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Procedure updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating procedure: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating procedure")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:procedure_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit procedure")
                return handler403(request, "Access denied to edit procedure")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure edit")

class ProcedureDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting procedures"""
    model = Procedure
    success_url = reverse_lazy('procedure_management:procedure_list')
    
    def delete(self, request, *args, **kwargs):
        try:
            procedure = self.get_object()
            logger.info(f"Procedure {procedure.pk} deleted by {request.user}")
            messages.success(request, "Procedure deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting procedure: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting procedure")
            return handler500(request, "Error deleting procedure")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete procedure")
                return handler403(request, "Access denied to delete procedure")

            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing procedure deletion")