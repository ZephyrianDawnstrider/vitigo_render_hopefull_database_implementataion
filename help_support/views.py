# Python Standard Library imports
import logging
from datetime import timedelta, datetime

# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db import transaction

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import handler403, handler404, handler500
from .models import (
    SupportTicket, 
    SupportResponse, 
    FAQ, 
    KnowledgeBaseArticle, 
    SupportCategory, 
    SupportRating
)

# Configure logging
logger = logging.getLogger(__name__)

def get_template_path(base_template, role, module='help_support'):
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

class HelpSupportManagementView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_access(request.user, 'help_support'):
            messages.error(request, "You don't have permission to access Help & Support")
            return handler403(request, exception="Access Denied")
        return super().dispatch(request, *args, **kwargs)

    def get_template_name(self):
        return get_template_path('help_support_dashboard.html', self.request.user.role, 'help_support')

    def get(self, request):
        try:
            template_path = self.get_template_name()
            if not template_path:
                return handler403(request, exception="Unauthorized access")

            # Fetch data with try-except blocks
            try:
                support_tickets = SupportTicket.objects.all()
                support_responses = SupportResponse.objects.all()
                faqs = FAQ.objects.all()
                knowledge_base_articles = KnowledgeBaseArticle.objects.all()
                support_categories = SupportCategory.objects.all()
                support_ratings = SupportRating.objects.all()
            except Exception as e:
                logger.error(f"Error fetching support data: {str(e)}")
                return handler500(request, exception="Error fetching support data")

            # Calculate statistics
            context = {
                'support_tickets': support_tickets,
                'support_responses': support_responses,
                'faqs': faqs,
                'knowledge_base_articles': knowledge_base_articles,
                'support_categories': support_categories,
                'support_ratings': support_ratings,
                'total_tickets': support_tickets.count(),
                'total_responses': support_responses.count(),
                'total_faqs': faqs.count(),
                'total_articles': knowledge_base_articles.count(),
                'total_categories': support_categories.count(),
                'total_ratings': support_ratings.count(),
                'user_role': request.user.role,
            }

            # Handle pagination
            try:
                paginator = Paginator(support_tickets, 10)
                page = request.GET.get('page')
                context['support_tickets'] = paginator.page(page)
                context['paginator'] = paginator
                context['page_obj'] = context['support_tickets']
            except PageNotAnInteger:
                context['support_tickets'] = paginator.page(1)
            except EmptyPage:
                context['support_tickets'] = paginator.page(paginator.num_pages)
            except Exception as e:
                logger.error(f"Pagination error: {str(e)}")
                messages.warning(request, "Error in pagination. Showing all results.")

            return render(request, template_path, context)

        except Exception as e:
            logger.exception(f"Unexpected error in HelpSupportManagementView: {str(e)}")
            return handler500(request, exception="An unexpected error occurred")