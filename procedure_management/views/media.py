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
from ..models import ProcedureMedia, Procedure
from ..forms import ProcedureMediaForm
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class MediaListView(LoginRequiredMixin, ListView):
    """View for listing procedure media files"""
    model = ProcedureMedia
    context_object_name = 'media_files'
    paginate_by = 12  # Show more items since these are media files
    
    def get_template_names(self):
        try:
            return [get_template_path(
                '_media/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading media list template")

    def get_queryset(self):
        queryset = ProcedureMedia.objects.select_related('procedure', 'uploaded_by')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(procedure__procedure_type__name__icontains=search_query)
            )
        
        file_type = self.request.GET.get('file_type')
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        procedure = self.request.GET.get('procedure')
        if procedure:
            queryset = queryset.filter(procedure_id=procedure)
        
        return queryset.order_by('-uploaded_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'procedures': Procedure.objects.all(),
            'file_types': dict(ProcedureMedia._meta.get_field('file_type').choices),
            'media_counts': {
                'total': self.get_queryset().count(),
                'images': self.get_queryset().filter(file_type='IMAGE').count(),
                'videos': self.get_queryset().filter(file_type='VIDEO').count(),
                'documents': self.get_queryset().filter(file_type='DOCUMENT').count(),
            }
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to media list")
                return handler403(request, "Access denied to media list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing media list")

class MediaDetailView(LoginRequiredMixin, DetailView):
    """View for displaying media file details"""
    model = ProcedureMedia
    context_object_name = 'media_file'
    
    def get_template_names(self):
        try:
            return [get_template_path(
                '_media/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading media detail template")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            media = self.get_object()
            if media.is_private and not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to private media")
                return handler403(request, "Access denied to private media")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing media details")

class MediaCreateView(LoginRequiredMixin, CreateView):
    """View for uploading new media files"""
    model = ProcedureMedia
    form_class = ProcedureMediaForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                '_media/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading media form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            form.instance.uploaded_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Media file uploaded successfully")
            return response
        except Exception as e:
            logger.error(f"Error uploading media: {str(e)}", exc_info=True)
            messages.error(self.request, "Error uploading media file")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:media_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to upload media")
                return handler403(request, "Access denied to upload media")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing media upload")

class MediaUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating media file details"""
    model = ProcedureMedia
    form_class = ProcedureMediaForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                '_media/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading media form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'is_edit': True,
            'media_file': self.get_object()
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Media file updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating media: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating media file")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:media_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit media")
                return handler403(request, "Access denied to edit media")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing media edit")

class MediaDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting media files"""
    model = ProcedureMedia
    success_url = reverse_lazy('procedure_management:media_list')

    def delete(self, request, *args, **kwargs):
        try:
            media = self.get_object()
            # Delete the actual file from storage
            media.file.delete(save=False)
            logger.info(f"Media file {media.pk} deleted by {request.user}")
            messages.success(request, "Media file deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting media: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting media file")
            return handler500(request, "Error deleting media file")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete media")
                return handler403(request, "Access denied to delete media")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing media deletion")
