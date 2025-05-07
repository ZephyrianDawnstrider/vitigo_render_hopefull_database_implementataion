from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from ..models import AssetAudit
from ..forms import AssetAuditForm
from ..utils import get_template_path

import logging
logger = logging.getLogger(__name__)

class TotalAuditsView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to view audits")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('audits/total_audits.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            # Get filter parameters
            search_query = request.GET.get('search', '')
            status = request.GET.get('status', '')
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')

            # Base queryset
            audits = AssetAudit.objects.select_related('asset').order_by('-audit_date')

            # Apply filters
            if search_query:
                audits = audits.filter(
                    Q(asset__name__icontains=search_query) |
                    Q(asset__asset_id__icontains=search_query) |
                    Q(conducted_by__icontains=search_query)
                )
            if status:
                audits = audits.filter(status=status)
            if date_from:
                audits = audits.filter(audit_date__gte=date_from)
            if date_to:
                audits = audits.filter(audit_date__lte=date_to)

            # Pagination
            page = request.GET.get('page', 1)
            paginator = Paginator(audits, 10)
            try:
                audits = paginator.page(page)
            except PageNotAnInteger:
                audits = paginator.page(1)
            except EmptyPage:
                audits = paginator.page(paginator.num_pages)

            context = {
                'audits': audits,
                'search_query': search_query,
                'selected_status': status,
                'date_from': date_from,
                'date_to': date_to,
                'status_choices': AssetAudit.STATUS_CHOICES,
                'has_filters': bool(search_query or status or date_from or date_to),
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': 'Asset Audits'
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in total audits view: {str(e)}")
            messages.error(request, "An error occurred while loading asset audits")
            return handler500(request, exception=str(e))

class CreateAssetAuditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to create audits")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('audits/create_audit.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            form = AssetAuditForm()
            context = {
                'form': form,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': 'Create Asset Audit'
            }
            return render(request, template_path, context)
        except Exception as e:
            logger.error(f"Error in create audit view: {str(e)}")
            messages.error(request, "An error occurred while loading the audit form")
            return handler500(request, exception=str(e))

    def post(self, request):
        try:
            form = AssetAuditForm(request.POST, request.FILES)
            if form.is_valid():
                audit = form.save()
                messages.success(request, "Asset audit created successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Asset audit created successfully',
                    'redirect_url': reverse('total_audits')
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error creating audit: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to create audit'
            }, status=500)

class AssetAuditDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to view audit details")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('audits/audit_detail.html', self.request.user.role, 'asset_management')

    def get(self, request, audit_id):
        try:
            audit = get_object_or_404(AssetAudit.objects.select_related('asset'), pk=audit_id)
            
            context = {
                'audit': audit,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': f'Audit Details - {audit.asset.name}'
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in audit detail view: {str(e)}")
            messages.error(request, "An error occurred while loading audit details")
            return handler500(request, exception=str(e))

class UpdateAssetAuditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to update audits")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('audits/update_audit.html', self.request.user.role, 'asset_management')

    def get(self, request, audit_id):
        try:
            audit = get_object_or_404(AssetAudit, pk=audit_id)
            form = AssetAuditForm(instance=audit)
            
            context = {
                'form': form,
                'audit': audit,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': f'Update Audit - {audit.asset.name}'
            }
            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in update audit view: {str(e)}")
            messages.error(request, "An error occurred while loading the audit form")
            return handler500(request, exception=str(e))

    def post(self, request, audit_id):
        try:
            audit = get_object_or_404(AssetAudit, pk=audit_id)
            form = AssetAuditForm(request.POST, instance=audit)
            if form.is_valid():
                form.save()
                messages.success(request, "Asset audit updated successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Asset audit updated successfully',
                    'redirect_url': reverse('audit_detail', args=[audit_id])
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error updating audit: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to update audit'
            }, status=500)

class CompleteAssetAuditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to complete audits")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, audit_id):
        try:
            audit = get_object_or_404(AssetAudit, pk=audit_id)
            
            if audit.status == 'COMPLETED':
                messages.error(request, "Audit is already completed")
            else:
                audit.status = 'COMPLETED'
                audit.save()
                messages.success(request, f"Audit for {audit.asset.name} completed successfully")
            
            return redirect('audit_detail', audit_id=audit_id)
            
        except Exception as e:
            logger.error(f"Error completing audit {audit_id}: {str(e)}")
            messages.error(request, "Error completing audit")
            return redirect('total_audits')

class CancelAssetAuditView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to cancel audits")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, audit_id):
        try:
            audit = get_object_or_404(AssetAudit, pk=audit_id)
            
            if audit.status != 'PLANNED':
                messages.error(request, "Only planned audits can be cancelled")
            else:
                audit.status = 'CANCELLED'
                audit.save()
                messages.success(request, f"Audit for {audit.asset.name} cancelled successfully")
            
            return redirect('audit_detail', audit_id=audit_id)
            
        except Exception as e:
            logger.error(f"Error cancelling audit {audit_id}: {str(e)}")
            messages.error(request, "Error cancelling audit")
            return redirect('total_audits')
