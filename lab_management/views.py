# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, F
from django.shortcuts import render
from django.utils import timezone
from django.views import View

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    LabTest,
    LabOrder,
    LabOrderItem,
    LabResult
)

# Configure logging
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module=''):
    """
    Resolves template path based on user role.
    Now uses the template_folder from Role model.
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        # Fallback for any legacy code
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    if module:
        return f'{role_folder}/{module}/{base_template}'
    return f'{role_folder}/{base_template}'

class LabManagementView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'lab_management'):
                messages.error(request, "You don't have permission to access Lab Management")
                return handler403(request, exception="Access denied to lab management")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in lab management dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing lab management")
            return handler500(request, exception=str(e))

    def get(self, request):
        try:
            template_path = get_template_path('lab_dashboard.html', request.user.role, 'lab_management')
            context = self.get_context_data()

            # Pagination for lab orders
            try:
                page = request.GET.get('page', 1)
                paginator = Paginator(context['lab_orders'], 10)
                context['lab_orders'] = paginator.page(page)
                context['paginator'] = paginator
            except PageNotAnInteger:
                context['lab_orders'] = paginator.page(1)
            except EmptyPage:
                context['lab_orders'] = paginator.page(paginator.num_pages)
            except Exception as e:
                logger.error(f"Pagination error: {str(e)}")
                messages.warning(request, "Error loading page data")

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in lab management view: {str(e)}")
            messages.error(request, "An error occurred while loading lab data")
            return handler500(request, exception=str(e))

    def get_context_data(self):
        try:
            lab_orders = LabOrder.objects.select_related(
                'patient__user',
                'ordered_by'
            ).prefetch_related(
                'items__lab_test',
                'items__result'
            )

            now = timezone.now()
            context = {
                'lab_orders': lab_orders,
                'pending_tests': lab_orders.filter(status='ORDERED').count(),
                'critical_results': LabResult.objects.filter(status='CRITICAL').count(),
                'completed_tests': lab_orders.filter(status='COMPLETED').count(),
                'monthly_revenue': LabOrderItem.objects.filter(
                    lab_order__status='COMPLETED',
                    lab_order__order_date__month=now.month,
                    lab_order__order_date__year=now.year
                ).aggregate(total=Sum('price'))['total'] or 0
            }

            return context
        except Exception as e:
            logger.error(f"Error getting lab context data: {str(e)}")
            return {
                'lab_orders': LabOrder.objects.none(),
                'pending_tests': 0,
                'critical_results': 0,
                'completed_tests': 0,
                'monthly_revenue': 0
            }