# urls.py

from django.urls import path
from .views import (
    reports as report_views,
)

app_name = 'reporting_and_analytics'

urlpatterns = [
    path('', report_views.ReportsAnalyticsManagementView.as_view(), name='reports_analytics_management'),
    path('category/<int:category_id>/reports/', 
         report_views.CategoryReportsView.as_view(), 
         name='category_reports'),
    path('report/<int:report_id>/exports/', 
         report_views.ReportExportsView.as_view(), 
         name='report_exports'),
]