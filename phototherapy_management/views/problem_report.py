# Standard library imports
import logging
from datetime import timedelta

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.generic import View
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

# Local/application imports
from error_handling.views import handler500, handler403
from phototherapy_management.models import PhototherapySession, ProblemReport
from access_control.permissions import PermissionManager
from phototherapy_management.utils import get_template_path
from phototherapy_management.forms import ProblemReportForm

# Configure logger  
logger = logging.getLogger(__name__)

# Get user model
User = get_user_model()

class ReportProblemView(LoginRequiredMixin, CreateView):
    model = ProblemReport
    form_class = ProblemReportForm
    success_url = reverse_lazy('phototherapy_management')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            form.instance.reported_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, 'Problem report submitted successfully')
            return response
        except Exception as e:
            logger.error(f"Error saving problem report: {str(e)}")
            messages.error(self.request, "Error submitting problem report")
            return self.form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        try:
            if not PermissionManager.check_module_access(request.user, 'phototherapy_management'):
                logger.warning(
                    f"Access denied to problem reporting for user {request.user.id}"
                )
                messages.error(request, "You don't have permission to report problems")
                return handler403(request, exception="Access Denied")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in problem report dispatch: {str(e)}")
            messages.error(request, "An error occurred while accessing the page")
            return redirect('dashboard')

    def get_template_names(self):
        try:
            return [get_template_path(
                'report_problem.html',
                self.request.user.role,
                'phototherapy_management'
            )]
        except Exception as e:
            logger.error(f"Error getting template: {str(e)}")
            return ['phototherapy_management/default_report_problem.html']