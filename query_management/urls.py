from django.urls import path
from .views import (
    attachments as attachment_views,
    dashboard as dashboard_views,
    queries as query_views,
    exports as export_views,
    tags as tag_views,
    updates as update_views,
)
from .api_views import SimpleQueryCreateAPI

urlpatterns = [
    # Dashboard/Main Views
    path('', dashboard_views.QueryManagementView.as_view(), 
         name='query_management'),

    # Query CRUD Operations
    path('create/', query_views.QueryCreateView.as_view(), 
         name='query_create'),
    path('<int:query_id>/', query_views.QueryDetailView.as_view(), 
         name='query_detail'),
    path('<int:query_id>/update/', query_views.QueryUpdateView.as_view(), 
         name='query_update'),
    path('<int:query_id>/delete/', query_views.QueryDeleteView.as_view(), 
         name='query_delete'),

    # Query Status Management
    path('<int:query_id>/assign/', query_views.QueryAssignView.as_view(), 
         name='query_assign'),
    path('<int:query_id>/update-status/', 
         query_views.QueryUpdateStatusView.as_view(), 
         name='query_update_status'),
    path('<int:query_id>/resolve/', query_views.QueryResolveView.as_view(), 
         name='query_resolve'),

    # Analytics and Reporting
    path('trend-data/', query_views.QueryTrendDataView.as_view(), 
         name='query_trend_data'),
    path('response-time-data/', 
         query_views.QueryResponseTimeDataView.as_view(), 
         name='query_response_time_data'),
    path('staff-performance-data/', 
         query_views.QueryStaffPerformanceDataView.as_view(), 
         name='query_staff_performance_data'),

    # Export Functionality
    path('export/', export_views.QueryExportView.as_view(), 
         name='query_export'),

    # API Endpoints
    path('api/create-simple-query/', SimpleQueryCreateAPI.as_view(), 
         name='api_create_simple_query'),
]