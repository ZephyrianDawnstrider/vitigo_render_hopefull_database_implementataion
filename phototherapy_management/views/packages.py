from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q, Sum
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy

from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from phototherapy_management.models import PhototherapyPackage, PhototherapyPlan, PhototherapyType
from phototherapy_management.utils import get_template_path
from ..forms import PhototherapyPackageForm

import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_protect, name='dispatch')
class PhototherapyPackagesListView(LoginRequiredMixin, ListView):
    model = PhototherapyPackage
    context_object_name = 'packages'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'phototherapy_management'):
                messages.error(request, "You don't have permission to access Phototherapy Packages")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in phototherapy packages dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return handler500(request, exception=str(e))

    def get_template_names(self):
        try:
            return [get_template_path(
                'packages/package_list.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_package_list.html']

    def get_queryset(self):
        try:
            queryset = PhototherapyPackage.objects.select_related(
                'therapy_type',
                'created_by'
            )
            
            # Search functionality
            search_query = self.request.GET.get('search')
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            
            # Filter by status
            status = self.request.GET.get('status')
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
                
            # Filter by therapy type
            therapy_type = self.request.GET.get('therapy_type')
            if therapy_type:
                queryset = queryset.filter(therapy_type_id=therapy_type)

            # Sort functionality
            sort_by = self.request.GET.get('sort', '-created_at')
            valid_sort_fields = ['name', '-name', 'number_of_sessions', 
                               '-number_of_sessions', 'total_cost', '-total_cost',
                               'created_at', '-created_at']
            if sort_by in valid_sort_fields:
                queryset = queryset.order_by(sort_by)
            
            return queryset
        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            return PhototherapyPackage.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            packages = context['packages']
            
            # Add filter values to context
            context.update({
                'search_query': self.request.GET.get('search', ''),
                'current_status': self.request.GET.get('status', ''),
                'current_therapy_type': self.request.GET.get('therapy_type', ''),
                'current_sort': self.request.GET.get('sort', '-created_at'),
                
                # Add summary statistics
                'total_packages': PhototherapyPackage.objects.count(),
                'active_packages': PhototherapyPackage.objects.filter(is_active=True).count(),
                'featured_packages': PhototherapyPackage.objects.filter(is_featured=True).count(),
                
                # Add permissions
                'can_add': PermissionManager.check_module_modify(self.request.user, 'phototherapy_management'),
                'can_edit': PermissionManager.check_module_modify(self.request.user, 'phototherapy_management'),
                'can_delete': PermissionManager.check_module_delete(self.request.user, 'phototherapy_management'),
                
                # Add therapy types for filtering
                'therapy_types': PhototherapyType.objects.filter(is_active=True),
            })
            
        except Exception as e:
            logger.error(f"Error in get_context_data: {str(e)}")
            messages.error(self.request, "Error loading some package data")
            
        return context

@method_decorator(csrf_protect, name='dispatch')
class CreatePackageView(LoginRequiredMixin, CreateView):
    model = PhototherapyPackage
    form_class = PhototherapyPackageForm
    success_url = reverse_lazy('package_list')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_modify(request.user, 'phototherapy_management'):
                messages.error(request, "You don't have permission to create packages")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in create package dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return handler500(request, exception=str(e))

    def get_template_names(self):
        try:
            return [get_template_path(
                'packages/create_package.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_create_package.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                # Add therapy types for dropdown
                'therapy_types': PhototherapyType.objects.filter(is_active=True),
                
                # Add permissions for conditional rendering
                'can_add': PermissionManager.check_module_modify(self.request.user, 'phototherapy_management'),
                
                # Add summary data for reference
                'total_packages': PhototherapyPackage.objects.count(),
                'active_packages': PhototherapyPackage.objects.filter(is_active=True).count(),
            })
        except Exception as e:
            logger.error(f"Error in get_context_data: {str(e)}")
            messages.error(self.request, "Error loading form data")
        return context

    def form_valid(self, form):
        try:
            # Set the created_by field to current user
            form.instance.created_by = self.request.user
            
            # Save the package
            response = super().form_valid(form)
            
            # Add success message
            messages.success(self.request, f"Package '{form.instance.name}' created successfully")
            
            # Log the action
            logger.info(f"Package created: {form.instance.id} by user {self.request.user.id}")
            
            return response
        except Exception as e:
            logger.error(f"Error creating package: {str(e)}")
            messages.error(self.request, "Error creating package. Please try again.")
            return super().form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below")
        logger.warning(f"Invalid package form submission: {form.errors}")
        return super().form_invalid(form)

@method_decorator(csrf_protect, name='dispatch')
class EditPackageView(LoginRequiredMixin, UpdateView):
    model = PhototherapyPackage
    form_class = PhototherapyPackageForm
    success_url = reverse_lazy('package_list')

    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_modify(request.user, 'phototherapy_management'):
                messages.error(request, "You don't have permission to edit packages")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in edit package dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return handler500(request, exception=str(e))

    def get_template_names(self):
        try:
            return [get_template_path(
                'packages/edit_package.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_edit_package.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update({
                'therapy_types': PhototherapyType.objects.filter(is_active=True),
                'can_edit': PermissionManager.check_module_modify(self.request.user, 'phototherapy_management'),
                'package': self.get_object()
            })
        except Exception as e:
            logger.error(f"Error in get_context_data: {str(e)}")
            messages.error(self.request, "Error loading form data")
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Package '{form.instance.name}' updated successfully")
            logger.info(f"Package updated: {form.instance.id} by user {self.request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error updating package: {str(e)}")
            messages.error(self.request, "Error updating package. Please try again.")
            return super().form_invalid(form)
