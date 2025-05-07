# Python Standard Library imports
import csv
import logging
from datetime import datetime, timedelta

# Third-party imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Django core imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.core.paginator import (
    EmptyPage,
    PageNotAnInteger,
    Paginator,
)
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    Q,
    fields,
)
from django.db.models.functions import (
    ExtractHour,
    TruncDate,
    TruncMonth,
    TruncWeek,
)
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic.edit import CreateView

# Local application imports
from access_control.models import Role
from access_control.permissions import PermissionManager
from error_handling.views import (
    handler403,
    handler404,
    handler500,
)
from patient_management.models import Patient

# Current app imports
from .dashboard import QueryManagementView
from ..forms import QueryCreateForm
from ..models import (
    Query,
    QueryAttachment,
    QueryTag,
    QueryUpdate,
)
from ..utils import (
    get_template_path,
    send_query_notification,
)

# Logger configuration
logger = logging.getLogger(__name__)

# Get the User model
User = get_user_model()

class QueryDetailView(LoginRequiredMixin, View):
    def get(self, request, query_id):
        try:
            if not PermissionManager.check_module_access(request.user, 'query_management'):
                messages.error(request, "You don't have permission to view query details")
                return handler403(request, exception="Access Denied")

            query = get_object_or_404(Query, query_id=query_id)
            template_path = get_template_path('queries/detail.html', request.user.role, 'query_management')
            
            if not template_path:
                return HttpResponse("Unauthorized access", status=403)

            # Get query with all essential relationships
            query = get_object_or_404(
                Query.objects.select_related(
                    'user',
                    'assigned_to'
                ).prefetch_related(
                    'updates',
                    'attachments',
                    'tags'
                ),
                query_id=query_id
            )

            # Get patient profile if it exists
            patient_profile = None
            if query.user:
                try:
                    patient_profile = Patient.objects.get(user=query.user)
                except Patient.DoesNotExist:
                    pass

            context = {
                'query': query,
                'user_details': {
                    'name': query.user.get_full_name() if query.user else 'Anonymous',
                    'email': query.user.email if query.user else query.contact_email,
                    'role': query.user.role if query.user else None,
                },
                'patient_profile': patient_profile,
                'assigned_to_details': {
                    'name': query.assigned_to.get_full_name() if query.assigned_to else 'Unassigned',
                    'email': query.assigned_to.email if query.assigned_to else None,
                    'role': query.assigned_to.role if query.assigned_to else None,
                },
                'updates': query.updates.all().order_by('-created_at'),
                'attachments': query.attachments.all(),
                'tags': query.tags.all(),
            }

            return render(request, template_path, context)

        except Query.DoesNotExist:
            return handler404(request, exception="Query not found")
        except Exception as e:
            return handler500(request, exception=str(e))

class QueryCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'query_management')

    def dispatch(self, request, *args, **kwargs):
        if not self.test_func():
            messages.error(request, "You don't have permission to create queries")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)
        
    def get(self, request):
        try:
            template_path = get_template_path('queries/create.html', request.user.role, 'query_management')
            
            if not template_path:
                return HttpResponse("Unauthorized access", status=403)
                
            form = QueryCreateForm()
            context = {
                'form': form
            }
            return render(request, template_path, context)
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponse(f"An error occurred: {str(e)}", status=500)
            
    def post(self, request):
        try:
            form = QueryCreateForm(request.POST)
            if form.is_valid():
                query = form.save(commit=False)
                if not form.cleaned_data.get('user'):
                    query.user = request.user
                query.save()
                form.save_m2m()
                
                # Send notification for new query
                send_query_notification(query, 'created')
                
                messages.success(request, "Query created successfully")
                return redirect('query_management')
                
            # If form invalid, re-render with errors
            template_path = get_template_path('query_create.html', request.user.role, 'query_management')
            return render(request, template_path, {'form': form})
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponse(f"An error occurred: {str(e)}", status=500)
        

class QueryUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'query_management')
    
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_modify(self.request.user, 'query_management'):
            messages.error(request, "You don't have permission to update queries")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)
        
    def get(self, request, query_id):
        try:
            template_path = get_template_path('queries/update.html', request.user.role, 'query_management')
            
            if not template_path:
                return HttpResponse("Unauthorized access", status=403)
            
            query = get_object_or_404(Query, query_id=query_id)
            form = QueryCreateForm(instance=query)  # Reuse create form
            
            context = {
                'form': form,
                'query': query
            }
            return render(request, template_path, context)
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponse(f"An error occurred: {str(e)}", status=500)
            
    def post(self, request, query_id):
        try:
            query = get_object_or_404(Query, query_id=query_id)
            form = QueryCreateForm(request.POST, instance=query)
            
            if form.is_valid():
                query = form.save(commit=False)
                old_status = query.status
                
                # Check if status changed to resolved
                if query.status == 'RESOLVED' and not query.resolved_at:
                    query.resolved_at = timezone.now()
                
                query.save()
                form.save_m2m()
                
                # Notify if status changed
                if old_status != query.status:
                    send_query_notification(
                        query, 
                        'status_updated',
                        old_status=old_status,
                        new_status=query.status
                    )
                
                messages.success(request, "Query updated successfully")
                return redirect('query_detail', query_id=query.query_id)
            
            template_path = get_template_path('query_update.html', request.user.role, 'query_management')
            return render(request, template_path, {'form': form, 'query': query})
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return HttpResponse(f"An error occurred: {str(e)}", status=500)
        

class QueryDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_delete(self.request.user, 'query_management')
        
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_delete(self.request.user, 'query_management'):
            messages.error(request, "You don't have permission to delete queries")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, query_id):
        try:
            query = get_object_or_404(Query, query_id=query_id)
            query_number = query.query_id  # Store for message
            query.delete()
            
            messages.success(request, f"Query #{query_number} deleted successfully")
            return redirect('query_management')
            
        except Exception as e:
            messages.error(request, f"Error deleting query: {str(e)}")
            return HttpResponse(f"Error deleting query: {str(e)}", status=500)
        

class QueryAssignView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return PermissionManager.check_module_modify(self.request.user, 'query_management')
    
    def dispatch(self, request, *args, **kwargs):
        if not PermissionManager.check_module_modify(self.request.user, 'query_management'):
            messages.error(request, "You don't have permission to assign queries")
            return handler403(request, exception="Insufficient Permissions")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, query_id):
        try:
            query = get_object_or_404(Query, query_id=query_id)
            staff_id = request.POST.get('assigned_to')
            
            if staff_id:
                User = get_user_model()
                staff = get_object_or_404(User, id=staff_id)
                previous_assignee = query.assigned_to
                query.assigned_to = staff
                query.save()
                
                # Send notification to newly assigned staff
                send_query_notification(
                    query, 
                    'assigned', 
                    recipient=staff,
                    assigned_by=request.user
                )
                
                # Notify query creator if they exist and are different from the assignee
                if query.user and query.user != staff:
                    send_query_notification(
                        query,
                        'status_updated',
                        recipient=query.user,
                        update_content=f"Query assigned to {staff.get_full_name()}"
                    )
                
                # Notify previous assignee if exists and different from new assignee
                if previous_assignee and previous_assignee != staff:
                    send_query_notification(
                        query,
                        'status_updated',
                        recipient=previous_assignee,
                        update_content=f"Query reassigned to {staff.get_full_name()}"
                    )
                
                # Create a query update to log the assignment
                QueryUpdate.objects.create(
                    query=query,
                    user=request.user,
                    content=f"Query assigned to {staff.get_full_name()}"
                )
                
                messages.success(request, f"Query #{query.query_id} assigned to {staff.get_full_name()}")
            else:
                messages.error(request, "No staff member selected")
                
            return redirect('query_management')
            
        except Exception as e:
            messages.error(request, f"Error assigning query: {str(e)}")
            return redirect('query_management')

class QueryUpdateStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, query_id):
        try:
            query = get_object_or_404(Query, query_id=query_id)
            update_content = request.POST.get('update_content')
            new_status = request.POST.get('new_status')
            
            if update_content:
                # Create query update
                update = QueryUpdate.objects.create(
                    query=query,
                    user=request.user,
                    content=update_content
                )
                
                # Handle file attachments
                files = request.FILES.getlist('attachments')
                for file in files:
                    QueryAttachment.objects.create(
                        query=query,
                        file=file
                    )
                
                # Update query status if provided
                if new_status and new_status != query.status:
                    old_status = query.status
                    query.status = new_status
                    if new_status == 'RESOLVED':
                        query.resolved_at = timezone.now()
                        # Send resolution notification
                        send_query_notification(query, 'resolved')
                    else:
                        # Send status update notification
                        send_query_notification(
                            query, 
                            'status_updated',
                            old_status=old_status,
                            new_status=new_status
                        )
                    query.save()
                
                # Notify query owner about the update
                if query.user and query.user != request.user:
                    send_query_notification(
                        query,
                        'status_updated',
                        recipient=query.user,
                        update_content=update_content
                    )
                
                messages.success(request, f"Update added to Query #{query.query_id}")
                if files:
                    messages.info(request, f"{len(files)} file(s) attached successfully")
            else:
                messages.error(request, "Update content is required")
                
            return redirect('query_detail', query_id=query.query_id)
            
        except Exception as e:
            messages.error(request, f"Error adding update: {str(e)}")
            return redirect('query_detail', query_id=query_id)

class QueryResolveView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, query_id):
        try:
            query = get_object_or_404(Query, query_id=query_id)
            
            # Only allow resolving if query isn't already resolved/closed
            if query.status not in ['RESOLVED', 'CLOSED']:
                query.status = 'RESOLVED'
                query.resolved_at = timezone.now()
                query.save()
                
                # Create a query update to log the resolution
                QueryUpdate.objects.create(
                    query=query,
                    user=request.user,
                    content=f"Query marked as resolved by {request.user.get_full_name()}"
                )
                
                # Send resolution notification
                send_query_notification(
                    query, 
                    'resolved',
                    resolver=request.user.get_full_name()
                )
                
                messages.success(request, f"Query #{query.query_id} has been marked as resolved")
            else:
                messages.warning(request, "Query is already resolved or closed")
                
            return redirect('query_management')
            
        except Exception as e:
            messages.error(request, f"Error resolving query: {str(e)}")
            return redirect('query_management')

class QueryTrendDataView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            days = int(request.GET.get('days', 30))
            queryset = Query.objects.all()
            data = QueryManagementView().get_query_trend_data(queryset, days)
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class QueryResponseTimeDataView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            period = request.GET.get('period', 'day')
            queryset = Query.objects.all()
            data = QueryManagementView().get_response_time_data(queryset, period)
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class QueryStaffPerformanceDataView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            days = int(request.GET.get('days', 30))
            queryset = Query.objects.all()
            data = QueryManagementView().get_staff_performance(queryset, days)
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

