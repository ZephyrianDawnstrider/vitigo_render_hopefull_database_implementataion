from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
import logging
from django.contrib import messages
from django.shortcuts import redirect

from phototherapy_management.models import PhototherapyPayment
from phototherapy_management.utils import get_template_path

logger = logging.getLogger(__name__)

class PaymentListView(LoginRequiredMixin, View):
    def get(self, request):
        # Get filter parameters
        date_filter = request.GET.get('date_filter', 'all')
        payment_type = request.GET.get('payment_type', '')
        payment_status = request.GET.get('payment_status', '')
        search_query = request.GET.get('search', '')
        
        # Base queryset with related data
        payments = PhototherapyPayment.objects.select_related(
            'plan__patient',
            'session',
            'recorded_by'
        ).order_by('-payment_date')

        # Add search functionality
        if search_query:
            payments = payments.filter(
                Q(receipt_number__icontains=search_query) |
                Q(plan__patient__first_name__icontains=search_query) |
                Q(plan__patient__last_name__icontains=search_query) |
                Q(transaction_id__icontains=search_query) |
                Q(amount__icontains=search_query)
            )

        # Apply filters
        if date_filter == 'today':
            payments = payments.filter(payment_date__date=timezone.now().date())
        elif date_filter == 'week':
            start_date = timezone.now().date() - timedelta(days=7)
            payments = payments.filter(payment_date__date__gte=start_date)
        elif date_filter == 'month':
            start_date = timezone.now().date() - timedelta(days=30)
            payments = payments.filter(payment_date__date__gte=start_date)

        if payment_type:
            payments = payments.filter(payment_type=payment_type)
        if payment_status:
            payments = payments.filter(status=payment_status)

        # Calculate statistics
        total_amount = payments.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or 0
        payment_count = payments.count()
        pending_count = payments.filter(status='PENDING').count()
        
        # Update payment method distribution aggregation
        payment_methods = payments.filter(status='COMPLETED').values(
            'payment_method'
        ).annotate(
            count=Count('id')
        ).order_by('payment_method')  # Add ordering
        
        # Calculate total for each method and format display name
        payment_methods = [
            {
                'method': payment['payment_method'],
                'display_name': dict(PhototherapyPayment.PAYMENT_METHOD).get(payment['payment_method'], ''),
                'count': payment['count']
            }
            for payment in payment_methods
        ]

        # Add pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(payments, 10)  # Show 10 payments per page
        try:
            payments = paginator.page(page)
        except Exception as e:
            logger.error(f"Pagination error: {str(e)}")
            payments = paginator.page(1)

        context = {
            'payments': payments,
            'total_amount': total_amount,
            'payment_count': payment_count,
            'pending_count': pending_count,
            'payment_methods': payment_methods,
            'selected_date_filter': date_filter,
            'selected_payment_type': payment_type,
            'selected_payment_status': payment_status,
            'payment_type_choices': PhototherapyPayment.PAYMENT_TYPE,
            'payment_status_choices': PhototherapyPayment.PAYMENT_STATUS,
            'page_obj': payments,  # Add this for pagination template
            'search_query': search_query,
        }

        template_path = get_template_path(
            'payment_list.html',
            request.user.role,
            'phototherapy_management'
        )

        return render(request, template_path, context)

class PaymentDetailView(LoginRequiredMixin, View):
    def get(self, request, payment_id):
        try:
            payment = PhototherapyPayment.objects.select_related(
                'plan__patient',
                'session',
                'recorded_by'
            ).get(id=payment_id)

            context = {
                'payment': payment,
                'plan': payment.plan,
                'patient': payment.plan.patient,
                'session': payment.session,
                'recorded_by': payment.recorded_by
            }

            template_path = get_template_path(
                'payment_detail.html',
                request.user.role,
                'phototherapy_management'
            )

            return render(request, template_path, context)
            
        except PhototherapyPayment.DoesNotExist:
            messages.error(request, "Payment not found")
            return redirect('payment_list')
        except Exception as e:
            logger.error(f"Error viewing payment details: {str(e)}")
            messages.error(request, "An error occurred while loading payment details")
            return redirect('payment_list')
