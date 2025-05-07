# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, F, Count
from django.shortcuts import render
from django.utils import timezone
from django.views import View

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import ItemCategory, StockItem, StockMovement

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

class StockManagementView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'stock_management'):
                messages.error(request, "You don't have permission to access Stock Management")
                return handler403(request, exception="Access denied to stock management")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in stock management dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing stock management")
            return handler500(request, exception=str(e))

    def get(self, request):
        try:
            template_path = get_template_path('stock_dashboard.html', request.user.role, 'stock_management')
            context = self.get_context_data()

            # Pagination for stock items
            try:
                page = request.GET.get('page', 1)
                paginator = Paginator(context['items'], 10)
                context['items'] = paginator.page(page)
                context['paginator'] = paginator
            except PageNotAnInteger:
                context['items'] = paginator.page(1)
            except EmptyPage:
                context['items'] = paginator.page(paginator.num_pages)
            except Exception as e:
                logger.error(f"Pagination error: {str(e)}")
                messages.warning(request, "Error loading page data")

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in stock management view: {str(e)}")
            messages.error(request, "An error occurred while loading stock data")
            return handler500(request, exception=str(e))

    def get_context_data(self):
        try:
            stock_items = StockItem.objects.select_related(
                'category'
            ).prefetch_related(
                'movements'
            ).all()

            now = timezone.now()
            context = {
                'items': stock_items,
                'categories': ItemCategory.objects.all(),
                'total_items': stock_items.count(),
                'low_stock_count': stock_items.filter(
                    current_quantity__lte=F('reorder_point')
                ).count(),
                'total_stock_value': stock_items.aggregate(
                    total_value=Sum(F('current_quantity') * F('unit_price'))
                )['total_value'] or 0,
                'monthly_transactions': StockMovement.objects.filter(
                    date__month=now.month,
                    date__year=now.year
                ).count(),
            }

            return context
        except Exception as e:
            logger.error(f"Error getting stock context data: {str(e)}")
            return {
                'items': StockItem.objects.none(),
                'categories': ItemCategory.objects.none(),
                'total_items': 0,
                'low_stock_count': 0,
                'total_stock_value': 0,
                'monthly_transactions': 0
            }