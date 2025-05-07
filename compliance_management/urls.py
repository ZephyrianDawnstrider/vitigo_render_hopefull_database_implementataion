from django.urls import path
from .views import (
    dashboard as dashboard_views,
    schedules as schedule_views,
    issues as issue_views,
    metrics as metrics_views,
    reminders as reminder_views,
    alerts as alert_views,
    reports as report_views,
    patient_groups as group_views,
    exports as export_views,
    notes as note_views,
)

app_name = 'compliance_management'

urlpatterns = [
    path('dashboard/', dashboard_views.ComplianceManagementDashboardView.as_view(), name='compliance_dashboard'),
    path('schedules/', schedule_views.ComplianceScheduleListView.as_view(), name='schedule_list'),
    path('schedules/<int:pk>/', schedule_views.ComplianceScheduleDetailView.as_view(), name='schedule_detail'),
    path('schedules/<int:pk>/edit/', schedule_views.ComplianceScheduleUpdateView.as_view(), name='schedule_edit'),
    path('schedules/<int:pk>/delete/', schedule_views.ComplianceScheduleDeleteView.as_view(), name='schedule_delete'),
    
    # Issue Management URLs
    path('issues/', issue_views.ComplianceIssueListView.as_view(), name='issue_list'),
    path('issues/create/', issue_views.ComplianceIssueCreateView.as_view(), name='issue_create'),
    path('issues/<int:pk>/', issue_views.ComplianceIssueDetailView.as_view(), name='issue_detail'),
    path('issues/<int:pk>/edit/', issue_views.ComplianceIssueUpdateView.as_view(), name='issue_edit'),
    path('issues/<int:pk>/delete/', issue_views.ComplianceIssueDeleteView.as_view(), name='issue_delete'),

    # Metrics Management URLs
    path('metrics/', metrics_views.ComplianceMetricListView.as_view(), name='metric_list'),
    path('metrics/create/', metrics_views.ComplianceMetricCreateView.as_view(), name='metric_create'),
    path('metrics/<int:pk>/', metrics_views.ComplianceMetricDetailView.as_view(), name='metric_detail'),
    path('metrics/<int:pk>/edit/', metrics_views.ComplianceMetricUpdateView.as_view(), name='metric_edit'),
    path('metrics/<int:pk>/delete/', metrics_views.ComplianceMetricDeleteView.as_view(), name='metric_delete'),

    # Reminder Management URLs
    path('reminders/', reminder_views.ComplianceReminderListView.as_view(), name='reminder_list'),
    path('reminders/create/', reminder_views.ComplianceReminderCreateView.as_view(), name='reminder_create'),
    path('reminders/<int:pk>/', reminder_views.ComplianceReminderDetailView.as_view(), name='reminder_detail'),
    path('reminders/<int:pk>/edit/', reminder_views.ComplianceReminderUpdateView.as_view(), name='reminder_edit'),
    path('reminders/<int:pk>/delete/', reminder_views.ComplianceReminderDeleteView.as_view(), name='reminder_delete'),
    path('reminders/history/<int:patient_id>/', reminder_views.ReminderHistoryView.as_view(), name='reminder_history'),

    # Alert Management URLs
    path('alerts/', alert_views.ComplianceAlertListView.as_view(), name='alert_list'),
    path('alerts/create/', alert_views.ComplianceAlertCreateView.as_view(), name='alert_create'),
    path('alerts/<int:pk>/', alert_views.ComplianceAlertDetailView.as_view(), name='alert_detail'),
    path('alerts/<int:pk>/edit/', alert_views.ComplianceAlertUpdateView.as_view(), name='alert_edit'),
    path('alerts/<int:pk>/delete/', alert_views.ComplianceAlertDeleteView.as_view(), name='alert_delete'),

    # Report Management URLs
    path('reports/', report_views.ComplianceReportListView.as_view(), name='report_list'),
    path('reports/create/', report_views.ComplianceReportCreateView.as_view(), name='report_create'),
    path('reports/<int:pk>/', report_views.ComplianceReportDetailView.as_view(), name='report_detail'),
    path('reports/<int:pk>/edit/', report_views.ComplianceReportUpdateView.as_view(), name='report_edit'),
    path('reports/<int:pk>/delete/', report_views.ComplianceReportDeleteView.as_view(), name='report_delete'),

    # Patient Group Management URLs
    path('groups/', group_views.PatientGroupListView.as_view(), name='group_list'),
    path('groups/create/', group_views.PatientGroupCreateView.as_view(), name='group_create'),
    path('groups/<int:pk>/', group_views.PatientGroupDetailView.as_view(), name='group_detail'),
    path('groups/<int:pk>/edit/', group_views.PatientGroupUpdateView.as_view(), name='group_edit'),
    path('groups/<int:pk>/delete/', group_views.PatientGroupDeleteView.as_view(), name='group_delete'),

    path('dashboard/export/', export_views.ComplianceDashboardExportView.as_view(), name='dashboard_export'),

    # Note Management URLs
    path('notes/', note_views.ComplianceNoteListView.as_view(), name='compliance_notes_list'),
    path('notes/create/', note_views.ComplianceNoteCreateView.as_view(), name='compliance_note_create'),
    path('notes/<int:pk>/', note_views.ComplianceNoteDetailView.as_view(), name='compliance_note_detail'),
    path('notes/<int:pk>/edit/', note_views.ComplianceNoteUpdateView.as_view(), name='compliance_note_edit'),
    path('notes/<int:pk>/delete/', note_views.ComplianceNoteDeleteView.as_view(), name='compliance_note_delete'),
]