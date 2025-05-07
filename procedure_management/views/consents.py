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
from ..models import Procedure, ProcedureCategory, ProcedureType, ConsentForm
from ..utils import get_template_path
from ..forms import ConsentFormForm

# Configure logging for this module
logger = logging.getLogger(__name__)

class ConsentFormListView(LoginRequiredMixin, ListView):
    """View for listing consent forms"""
    model = ConsentForm
    context_object_name = 'consent_forms'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'consents/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading consent list template")

    def get_queryset(self):
        queryset = ConsentForm.objects.select_related(
            'procedure',
            'procedure__patient',
            'procedure__procedure_type'
        ).order_by('-created_at')

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(procedure__patient__first_name__icontains=search_query) |
                Q(procedure__patient__last_name__icontains=search_query) |
                Q(procedure__procedure_type__name__icontains=search_query)
            )

        return queryset

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to consent list")
                return handler403(request, "Access denied to consent list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing consent list")

class ConsentFormDetailView(LoginRequiredMixin, DetailView):
    """View for displaying consent form details"""
    model = ConsentForm
    context_object_name = 'consent_form'

    def get_template_names(self):
        try:
            return [get_template_path(
                'consents/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading consent detail template")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
        
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view consent")
                return handler403(request, "Access denied to view consent")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing consent details")

class ConsentFormCreateView(LoginRequiredMixin, CreateView):
    """View for creating new consent forms"""
    model = ConsentForm
    form_class = ConsentFormForm
    template_name_suffix = '_form'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def get_template_names(self):
        try:
            return [get_template_path(
                'consents/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading consent form template")

    def form_valid(self, form):
        try:
            form.instance.created_at = timezone.now()
            response = super().form_valid(form)
            messages.success(self.request, "Consent form created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating consent form: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating consent form")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:consent_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create consent")
                return handler403(request, "Access denied to create consent")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing consent creation")

class ConsentFormUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating consent forms"""
    model = ConsentForm
    form_class = ConsentFormForm
    template_name_suffix = '_form'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['consent_form'] = self.get_object()
        return context

    def get_template_names(self):
        try:
            return [get_template_path(
                'consents/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading consent form template")

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Consent form updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating consent form: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating consent form")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:consent_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit consent")
                return handler403(request, "Access denied to edit consent")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing consent edit")

class ConsentFormDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting consent forms"""
    model = ConsentForm
    success_url = reverse_lazy('procedure_management:consent_list')

    def delete(self, request, *args, **kwargs):
        try:
            consent_form = self.get_object()
            logger.info(f"Consent form {consent_form.pk} deleted by {request.user}")
            messages.success(request, "Consent form deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting consent form: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting consent form")
            return handler500(request, "Error deleting consent form")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete consent")
                return handler403(request, "Access denied to delete consent")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing consent deletion")
