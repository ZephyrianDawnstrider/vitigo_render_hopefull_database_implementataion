# URLs configuration (add to urls.py)
from django.urls import path
from . import views, export_views

app_name = 'clinic_management'

urlpatterns = [
    path('', views.ClinicManagementDashboardView.as_view(), name='clinic_dashboard'),
    
    path('active_visits/', views.ActiveVisitsView.as_view(), name='active_visits'),

    path('active_checklists/', views.ActiveChecklistsView.as_view(), name='active_checklists'),

    path('visit_status_config/', views.VisitStatusConfigView.as_view(), name='visit_status_config'),

    path('completed_visits_report/', views.CompletedVisitsReportView.as_view(), name='completed_visits_report'),

    path('new_visit/', views.NewVisitView.as_view(), name='new_visit'),

    path('all_visits/', views.AllVisitsView.as_view(), name='all_visits'),

    path('visit_logs/', views.VisitLogsView.as_view(), name='visit_logs'),
    path('analytics/', views.VisitAnalyticsView.as_view(), name='visit_analytics'),
    
    path('checklist/new/', views.NewChecklistView.as_view(), name='new_checklist'),
    path('checklist/manage/', views.ManageChecklistsView.as_view(), name='manage_checklists'),
    path('checklist/items/', views.ChecklistItemsView.as_view(), name='checklist_items'),
    path('checklist/reports/', views.ChecklistReportsView.as_view(), name='checklist_reports'),
    
    path('visit-status/new/', views.NewVisitStatusView.as_view(), name='new_visit_status'),
    path('visit-status/<int:pk>/toggle/', views.ToggleVisitStatusView.as_view(), name='toggle_visit_status'),
    path('visit-status/<int:pk>/delete/', views.DeleteVisitStatusView.as_view(), name='delete_visit_status'),
    path('visit-status/<int:pk>/edit/', views.EditVisitStatusView.as_view(), name='edit_visit_status'),
    path('activities/', views.AllActivitiesView.as_view(), name='all_activities'),
    
    path('export/', export_views.ClinicDashboardExportView.as_view(), name='dashboard_export'),
    path('export/visits/', export_views.VisitDataExportView.as_view(), name='visit_data_export'),
    path('export/checklists/', export_views.ChecklistDataExportView.as_view(), name='checklist_data_export'),
    path('export/analytics/', export_views.AnalyticsExportView.as_view(), name='analytics_export'),
]
