# Standard library imports
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.views import View

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    GSTRate, Invoice, Payment, Expense,
    TDSEntry, FinancialYear, FinancialReport
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

class FinanceManagementView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'financial_management'):
                messages.error(request, "You don't have permission to access Financial Management")
                return handler403(request, exception="Access denied to financial management")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in finance management dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing financial management")
            return handler500(request, exception=str(e))

    def get(self, request):
        try:
            template_path = get_template_path('financial_dashboard.html', request.user.role, 'financial_management')
            context = self.get_context_data()

            # Pagination for invoices
            try:
                page = request.GET.get('page', 1)
                paginator = Paginator(context['invoices'], 10)
                context['invoices'] = paginator.page(page)
                context['paginator'] = paginator
            except PageNotAnInteger:
                context['invoices'] = paginator.page(1)
            except EmptyPage:
                context['invoices'] = paginator.page(paginator.num_pages)
            except Exception as e:
                logger.error(f"Pagination error: {str(e)}")
                messages.warning(request, "Error loading page data")

            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in finance management view: {str(e)}")
            messages.error(request, "An error occurred while loading financial data")
            return handler500(request, exception=str(e))

    def get_context_data(self):
        try:
            invoices = Invoice.objects.select_related(
                'patient__user',
                'created_by'
            ).prefetch_related(
                'items',
                'payments'
            )

            now = timezone.now()
            context = {
                'invoices': invoices,
                'payments': Payment.objects.select_related('invoice', 'received_by'),
                'expenses': Expense.objects.select_related('created_by', 'approved_by'),
                'tds_entries': TDSEntry.objects.select_related('expense'),
                'financial_years': FinancialYear.objects.all(),
                'financial_reports': FinancialReport.objects.select_related('financial_year', 'generated_by'),
                'total_invoices': invoices.count(),
                'total_payments': Payment.objects.aggregate(total_amount=Sum('amount'))['total_amount'] or 0,
                'total_expenses': Expense.objects.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0,
                'total_tds': TDSEntry.objects.aggregate(total_amount=Sum('tds_amount'))['total_amount'] or 0,
                'total_gst_collected': invoices.aggregate(total_gst=Sum('total_gst_amount'))['total_gst'] or 0,
            }

            # Calculate net profit
            context['net_profit'] = context['total_payments'] - context['total_expenses']

            # Round monetary values
            for key in ['total_payments', 'total_expenses', 'total_tds', 'total_gst_collected', 'net_profit']:
                context[key] = round(context[key], 2)

            return context
        except Exception as e:
            logger.error(f"Error getting finance context data: {str(e)}")
            return {
                'invoices': Invoice.objects.none(),
                'payments': Payment.objects.none(),
                'expenses': Expense.objects.none(),
                'tds_entries': TDSEntry.objects.none(),
                'financial_years': FinancialYear.objects.none(),
                'financial_reports': FinancialReport.objects.none(),
                'total_invoices': 0,
                'total_payments': 0,
                'total_expenses': 0,
                'total_tds': 0,
                'total_gst_collected': 0,
                'net_profit': 0
            }