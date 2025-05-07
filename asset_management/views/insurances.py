from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse

from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler500
from ..models import InsurancePolicy
from ..forms import InsurancePolicyForm
from ..utils import get_template_path

import logging
logger = logging.getLogger(__name__)

class TotalInsurancesView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to view insurances")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('insurances/total_insurances.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            # Get filter parameters
            search_query = request.GET.get('search', '')
            status = request.GET.get('status', '')
            date_from = request.GET.get('date_from', '')
            date_to = request.GET.get('date_to', '')

            # Base queryset
            insurances = InsurancePolicy.objects.select_related('asset').order_by('-start_date')

            # Apply filters
            if search_query:
                insurances = insurances.filter(
                    Q(asset__name__icontains=search_query) |
                    Q(policy_number__icontains=search_query) |
                    Q(provider__icontains=search_query)
                )
            if status:
                insurances = insurances.filter(status=status)
            if date_from:
                insurances = insurances.filter(start_date__gte=date_from)
            if date_to:
                insurances = insurances.filter(end_date__lte=date_to)

            # Update expired policies
            current_date = timezone.now().date()
            expired_policies = insurances.filter(
                end_date__lt=current_date,
                status='ACTIVE'
            )
            expired_policies.update(status='EXPIRED')

            # Pagination
            page = request.GET.get('page', 1)
            paginator = Paginator(insurances, 10)
            try:
                insurances = paginator.page(page)
            except PageNotAnInteger:
                insurances = paginator.page(1)
            except EmptyPage:
                insurances = paginator.page(paginator.num_pages)

            context = {
                'insurances': insurances,
                'search_query': search_query,
                'selected_status': status,
                'date_from': date_from,
                'date_to': date_to,
                'status_choices': InsurancePolicy.STATUS_CHOICES,
                'has_filters': bool(search_query or status or date_from or date_to),
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': 'Insurance Policies'
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in total insurances view: {str(e)}")
            messages.error(request, "An error occurred while loading insurance policies")
            return handler500(request, exception=str(e))

class CreateInsurancePolicyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to add insurance policies")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('insurances/create_insurance.html', self.request.user.role, 'asset_management')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            form = InsurancePolicyForm()
            context = {
                'form': form,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': 'Add Insurance Policy'
            }
            return render(request, template_path, context)
        except Exception as e:
            logger.error(f"Error in CreateInsurancePolicyView GET: {str(e)}")
            messages.error(request, "An error occurred while loading the insurance form.")
            return handler500(request, exception=str(e))

    def post(self, request):
        try:
            form = InsurancePolicyForm(request.POST)
            if form.is_valid():
                policy = form.save()
                messages.success(request, "Insurance policy added successfully")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Insurance policy added successfully',
                    'redirect_url': reverse('total_insurances')
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
            
        except Exception as e:
            logger.error(f"Error in CreateInsurancePolicyView POST: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to add insurance policy'
            }, status=500)

class InsurancePolicyDetailView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to view insurance details")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('insurances/insurance_detail.html', self.request.user.role, 'asset_management')

    def get(self, request, policy_id):
        try:
            policy = get_object_or_404(InsurancePolicy.objects.select_related('asset'), pk=policy_id)
            
            context = {
                'insurance': policy,
                'user_role': request.user.role.name if request.user.role else None,
                'module_name': 'Asset Management',
                'page_title': f'Insurance Details - {policy.policy_number}'
            }

            return render(request, self.get_template_name(), context)
        except Exception as e:
            logger.error(f"Error in insurance detail view: {str(e)}")
            messages.error(request, "An error occurred while loading insurance details")
            return handler500(request, exception=str(e))

class RenewInsurancePolicyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to renew insurance policies")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, policy_id):
        try:
            policy = get_object_or_404(InsurancePolicy, pk=policy_id)
            
            if policy.status != 'ACTIVE':
                messages.error(request, "Only active policies can be renewed")
            else:
                # Create new policy with extended dates
                new_policy = InsurancePolicy.objects.create(
                    asset=policy.asset,
                    policy_number=f"{policy.policy_number}-R",  # Add suffix for renewed policy
                    provider=policy.provider,
                    coverage_type=policy.coverage_type,
                    coverage_amount=policy.coverage_amount,
                    premium_amount=policy.premium_amount,
                    start_date=policy.end_date,  # Start from previous end date
                    end_date=policy.end_date + timezone.timedelta(days=365),  # Add one year
                    deductible=policy.deductible,
                    documents=policy.documents,
                    status='ACTIVE',
                    notes=f"Renewed from policy {policy.policy_number}"
                )
                
                # Update old policy status
                policy.status = 'RENEWED'
                policy.save()
                
                messages.success(request, f"Insurance policy renewed successfully. New policy number: {new_policy.policy_number}")
            
            return redirect('insurance_detail', policy_id=new_policy.id)
            
        except Exception as e:
            logger.error(f"Error renewing policy {policy_id}: {str(e)}")
            messages.error(request, "Error renewing insurance policy")
            return redirect('total_insurances')

class CancelInsurancePolicyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'asset_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to cancel insurance policies")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, policy_id):
        try:
            policy = get_object_or_404(InsurancePolicy, pk=policy_id)
            
            if policy.status != 'ACTIVE':
                messages.error(request, "Only active policies can be cancelled")
            else:
                policy.status = 'CANCELLED'
                policy.save()
                messages.success(request, f"Insurance policy {policy.policy_number} cancelled successfully")
            
            return redirect('insurance_detail', policy_id=policy_id)
            
        except Exception as e:
            logger.error(f"Error cancelling policy {policy_id}: {str(e)}")
            messages.error(request, "Error cancelling insurance policy")
            return redirect('total_insurances')
