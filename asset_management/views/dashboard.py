# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Local imports
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from ..models import Asset, MaintenanceSchedule, AssetAudit, InsurancePolicy
from ..utils import get_template_path
from ..constants import (
    DEFAULT_DASHBOARD_STATS, 
)

# Initialize logger
logger = logging.getLogger(__name__)

class AssetDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """Check if user has access to asset management module"""
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        """Handle unauthorized access"""
        try:
            if not self.test_func():
                messages.error(request, "You don't have permission to access Asset Management")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in asset management dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def get_template_name(self):
        """Get appropriate template based on user role"""
        try:
            return get_template_path('dashboard/dashboard.html', self.request.user.role, 'asset_management')
        except Exception as e:
            logger.error(f"Error getting template path: {str(e)}")
            return None

    def get_dashboard_stats(self):
        """Get key statistics for asset dashboard"""
        try:
            current_date = timezone.now().date()
            stats = {
                'total_assets': Asset.objects.filter(is_active=True).count(),
                'assets_in_use': Asset.objects.filter(status='IN_USE').count(),
                'maintenance_due': MaintenanceSchedule.objects.filter(
                    status='SCHEDULED',
                    scheduled_date__lte=current_date + timedelta(days=30)
                ).count(),
                'pending_audits': AssetAudit.objects.filter(
                    status__in=['PLANNED', 'IN_PROGRESS']
                ).count(),
                'expiring_insurance': InsurancePolicy.objects.filter(
                    status='ACTIVE',
                    end_date__lte=current_date + timedelta(days=30)
                ).count(),
            }
            return stats if any(stats.values()) else DEFAULT_DASHBOARD_STATS
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return DEFAULT_DASHBOARD_STATS

    def get(self, request, *args, **kwargs):
        try:
            # Get basic stats
            dashboard_stats = self.get_dashboard_stats()

            # Get status distribution data
            status_data = Asset.objects.values('status').annotate(
                count=Count('id')
            ).order_by('status')
            status_labels = [item['status'] for item in status_data]
            status_counts = [item['count'] for item in status_data]

            # Get category distribution data
            category_data = Asset.objects.values('category__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            category_labels = [item['category__name'] for item in category_data]
            category_counts = [item['count'] for item in category_data]

            # Get recent assets
            recent_assets = Asset.objects.select_related('category').order_by('-created_at')[:10]

            context = {
                'dashboard_stats': dashboard_stats,
                'status_labels': status_labels,
                'status_data': status_counts,
                'category_labels': category_labels,
                'category_data': category_counts,
                'recent_assets': recent_assets,
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in asset dashboard view: {str(e)}")
            messages.error(request, "An error occurred while loading the dashboard")
            return handler500(request)