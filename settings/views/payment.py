import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.core.exceptions import PermissionDenied

from settings.models import PaymentGateway
from settings.forms import PaymentGatewayForm
from access_control.permissions import PermissionManager
from settings.utils import get_template_path
from error_handling.views import handler403

logger = logging.getLogger(__name__)

class PaymentSettingsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                messages.error(request, "You don't have permission to access Payment Settings")
                return handler403(request, exception="Access Denied")

            # Get existing payment gateways
            payment_gateways = PaymentGateway.objects.all()
            
            # Initialize form
            gateway_form = PaymentGatewayForm()

            context = {
                'payment_gateways': payment_gateways,
                'gateway_form': gateway_form,
                'form_errors': {},
            }

            if 'form_errors' in request.session:
                context['form_errors'] = request.session.pop('form_errors')

            template_path = get_template_path('payment/payment_settings.html', request.user.role)
            return render(request, template_path, context)

        except Exception as e:
            logger.error(f"Error in PaymentSettingsView GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading payment settings")
            return redirect('dashboard')

    def post(self, request):
        try:
            if not PermissionManager.check_module_access(request.user, 'settings'):
                raise PermissionDenied("You don't have permission to modify payment settings")

            action = request.POST.get('action')

            if action == 'add_payment_gateway':
                return self.handle_payment_gateway(request)
            else:
                messages.error(request, "Invalid action specified")

        except PermissionDenied as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error in PaymentSettingsView POST: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while saving settings")

        return redirect('settings:payment_settings')

    def handle_payment_gateway(self, request):
        form = PaymentGatewayForm(request.POST)
        if form.is_valid():
            gateway = form.save(commit=False)
            gateway.created_by = request.user
            gateway.save()
            messages.success(request, "Payment gateway added successfully")
        else:
            request.session['form_errors'] = {'gateway_form': form.errors}
            messages.error(request, "Please correct the errors in the form")
        return redirect('settings:payment_settings')
