from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from access_control.permissions import PermissionManager
from django.contrib import messages

from settings.models import SettingHistory
from settings.views.views import get_template_path

class SettingHistoryView(LoginRequiredMixin, ListView):
    model = SettingHistory
    paginate_by = 20
    context_object_name = 'history_entries'

    def get_template_names(self):
        return [get_template_path('settings_history.html', self.request.user.role)]

    def get_queryset(self):
        queryset = SettingHistory.objects.select_related(
            'setting', 'setting__definition', 'changed_by'
        ).all()

        # Filter by date range if provided
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        # Filter by change type if provided
        change_type = self.request.GET.get('change_type')
        if change_type:
            queryset = queryset.filter(change_type=change_type)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['change_types'] = SettingHistory._meta.get_field('change_type').choices
        return context

    def get(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'settings'):
            messages.error(request, "You don't have permission to view settings history")
            return redirect('settings:settings_dashboard')
        return super().get(request, *args, **kwargs)
