from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from django.db.models import Q
from ..models import Notice
from access_control.permissions import PermissionManager
from hr_management.utils import get_template_path
from django.core.paginator import Paginator
from ..forms import NoticeForm
import logging

logger = logging.getLogger(__name__)

class NoticeListView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('notices/notice_list.html', self.request.user.role, 'hr_management')

    def get(self, request):
        try:
            search_query = request.GET.get('search', '')
            priority_filter = request.GET.get('priority', '')

            notices = Notice.objects.filter(
                Q(is_active=True) &
                (Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.now().date()))
            ).order_by('-priority', '-created_at')

            if search_query:
                notices = notices.filter(
                    Q(title__icontains=search_query) |
                    Q(content__icontains=search_query)
                )

            if priority_filter:
                notices = notices.filter(priority=priority_filter)

            paginator = Paginator(notices, 10)
            page = request.GET.get('page', 1)
            notices_page = paginator.get_page(page)

            context = {
                'notices': notices_page,
                'search_query': search_query,
                'priority_filter': priority_filter,
                'priority_choices': Notice.PRIORITY_CHOICES
            }
            return render(request, self.get_template_name(), context)

        except Exception as e:
            messages.error(request, "Error loading notices")
            return render(request, self.get_template_name(), {'notices': []})

class NoticeCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_access(self.request.user, 'hr_management')

    def get_template_name(self):
        return get_template_path('notices/new_notice.html', self.request.user.role, 'hr_management')

    def get(self, request):
        form = NoticeForm()
        return render(request, self.get_template_name(), {'form': form})

    def post(self, request):
        form = NoticeForm(request.POST)
        if form.is_valid():
            try:
                notice = form.save(commit=False)
                notice.created_by = request.user
                notice.save()
                messages.success(request, "Notice created successfully")
                return redirect('notice_list')
            except Exception as e:
                logger.error(f"Error creating notice: {str(e)}")
                messages.error(request, "Error creating notice")
        return render(request, self.get_template_name(), {'form': form})
