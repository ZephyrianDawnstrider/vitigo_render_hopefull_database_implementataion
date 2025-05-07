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
from ..models import ProcedureCategory
from ..forms import ProcedureCategoryForm
from ..utils import get_template_path

# Configure logging for this module
logger = logging.getLogger(__name__)

class ProcedureCategoryListView(LoginRequiredMixin, ListView):
    """View for listing procedure categories"""
    model = ProcedureCategory
    context_object_name = 'categories'
    paginate_by = 10
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'categories/list.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading category list template")

    def get_queryset(self):
        queryset = ProcedureCategory.objects.all()
        search_query = self.request.GET.get('search')
        if (search_query):
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_categories'] = self.get_queryset().filter(is_active=True).count()
        context['total_categories'] = self.get_queryset().count()
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to category list")
                return handler403(request, "Access denied to category list")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing category list")

class ProcedureCategoryDetailView(LoginRequiredMixin, DetailView):
    """View for displaying category details"""
    model = ProcedureCategory
    context_object_name = 'category'

    def get_template_names(self):
        try:
            return [get_template_path(
                'categories/detail.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading category detail template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        context['procedure_types'] = category.procedure_types.all()
        context['total_procedures'] = sum(pt.procedures.count() for pt in category.procedure_types.all())
        return context

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to view category")
                return handler403(request, "Access denied to view category")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing category details")

class ProcedureCategoryCreateView(LoginRequiredMixin, CreateView):
    """View for creating new procedure categories"""
    model = ProcedureCategory
    form_class = ProcedureCategoryForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'categories/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading category form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Category created successfully")
            return response
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}", exc_info=True)
            messages.error(self.request, "Error creating category")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:category_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to create category")
                return handler403(request, "Access denied to create category")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing category creation")

class ProcedureCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating procedure categories"""
    model = ProcedureCategory
    form_class = ProcedureCategoryForm
    
    def get_template_names(self):
        try:
            return [get_template_path(
                'categories/form.html',
                self.request.user.role,
                'procedure_management'
            )]
        except Exception as e:
            logger.error(f"Template retrieval error: {str(e)}")
            return handler500(self.request, "Error loading category form template")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['category'] = self.get_object()
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Category updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating category: {str(e)}", exc_info=True)
            messages.error(self.request, "Error updating category")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('procedure_management:category_detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to edit category")
                return handler403(request, "Access denied to edit category")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing category edit")

class ProcedureCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting procedure categories"""
    model = ProcedureCategory
    success_url = reverse_lazy('procedure_management:category_list')

    def delete(self, request, *args, **kwargs):
        try:
            category = self.get_object()
            if category.procedure_types.exists():
                messages.error(request, "Cannot delete category with existing procedure types")
                return self.render_to_response(self.get_context_data())
            
            logger.info(f"Category {category.pk} deleted by {request.user}")
            messages.success(request, "Category deleted successfully")
            return super().delete(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}", exc_info=True)
            messages.error(request, "Error deleting category")
            return handler500(request, "Error deleting category")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return handler401(request, "Authentication required")
            
        try:
            if not PermissionManager.check_module_access(request.user, 'procedure_management'):
                logger.warning(f"Access denied for user {request.user} to delete category")
                return handler403(request, "Access denied to delete category")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Dispatch error: {str(e)}", exc_info=True)
            return handler500(request, "Error accessing category deletion")
