from django.urls import path
from .views import (
    dashboard as d, 
    device as dv,
    protocol as pv,
    schedule as sv,
    report as rv,
    rfid as rf,
    problem_report as pr,
    reminder as rm,
    export as ev,
    home as hv,
    payment as pmv,
    packages as pm, 
)

urlpatterns = [
    path('', d.PhototherapyManagementView.as_view(), name='phototherapy_management'),
    path('new-treatment-plan/', d.NewTreatmentPlanView.as_view(), name='new_treatment_plan'),
    path('treatment-plans/', d.TreatmentPlanListView.as_view(), name='treatment_plan_list'),
    path('therapy-types/', d.PhototherapyTypeListView.as_view(), name='therapy_types_dashboard'),
    path('add-therapy-type/', d.AddPhototherapyTypeView.as_view(), name='add_therapy_type'),
    path('therapy-types/<int:pk>/edit/', d.EditPhototherapyTypeView.as_view(), name='edit_therapy_type'),
    path('therapy-types/<int:pk>/delete/', d.DeletePhototherapyTypeView.as_view(), name='delete_therapy_type'),
    path('therapy-type/<int:type_id>/details/', 
         d.get_therapy_type_details, 
         name='therapy_type_details'),
    path('treatment-plans/export/', ev.TreatmentPlanExportView.as_view(), name='export_treatment_plans'),
    path('treatment-plans/<int:pk>/', d.TreatmentPlanDetailView.as_view(), name='treatment_plan_detail'),
    path('treatment-plans/<int:pk>/activate/', d.ActivateTreatmentPlanView.as_view(), name='activate_treatment_plan'),
    path('treatment-plans/<int:pk>/deactivate/', d.DeactivateTreatmentPlanView.as_view(), name='deactivate_treatment_plan'),
    path('treatment-plans/<int:pk>/edit/', d.EditTreatmentPlanView.as_view(), name='edit_treatment_plan'),

    path('packages/', pm.PhototherapyPackagesListView.as_view(), name='package_list'),
    path('packages/create/', pm.CreatePackageView.as_view(), name='create_package'),
    path('packages/<int:pk>/edit/', pm.EditPackageView.as_view(), name='edit_package'),

    path('devices/', dv.DeviceManagementView.as_view(), name='device_management'),
    path('devices/register/', dv.RegisterDeviceView.as_view(), name='register_device'),
    path('devices/export/', ev.DeviceDataExportView.as_view(), name='export_device_data'),  
    path('devices/maintenance/schedule/', dv.ScheduleMaintenanceView.as_view(), name='schedule_maintenance'),
    path('devices/edit/<int:device_id>/', dv.EditDeviceView.as_view(), name='edit_device'),
    path('devices/<int:pk>/delete/', dv.DeleteDeviceView.as_view(), name='delete_device'),
    path('device/<int:device_id>/details/', 
         d.get_device_details, 
         name='device_details'),

    path('protocols/', pv.ProtocolManagementView.as_view(), name='protocol_management'),
    path('protocols/add/', pv.AddProtocolView.as_view(), name='add_protocol'),
    path('protocols/<int:protocol_id>/edit/', pv.EditProtocolView.as_view(), name='edit_protocol'),
    path('protocols/export/', ev.ProtocolExportView.as_view(), name='export_protocols'),
    path('protocols/<int:protocol_id>/', pv.ProtocolDetailView.as_view(), name='protocol_detail'),
    path('protocols/<int:protocol_id>/activate/', pv.ActivateProtocolView.as_view(), name='activate_protocol'),
    path('protocols/<int:protocol_id>/deactivate/', pv.DeactivateProtocolView.as_view(), name='deactivate_protocol'),
    path('protocol/<int:protocol_id>/details/', d.get_protocol_details, name='protocol_details'),

    path('schedules/', sv.ScheduleManagementView.as_view(), name='schedule_management'),
    path('schedule-session/', sv.ScheduleSessionView.as_view(), name='schedule_session'),
    path('session/<int:session_id>/', sv.SessionDetailView.as_view(), name='session_detail'),
    path('session/<int:session_id>/add-report/', sv.AddSessionReportView.as_view(), name='add_session_report'),
    path('session/<int:session_id>/update-notes/', sv.UpdateSessionNotesView.as_view(), name='update_session_notes'),
    path('session/<int:session_id>/update-rfid/', sv.UpdateRFIDTrackingView.as_view(), name='update_rfid_tracking'),
    path('session/<int:session_id>/update-status/', sv.UpdateSessionStatusView.as_view(), name='update_session_status'),
    path('session/<int:session_id>/update-remarks/', 
         sv.UpdateSessionRemarksView.as_view(), 
         name='update_session_remarks'),
    path('sessions/', sv.SessionListView.as_view(), name='session_list'),

    path('reports/', rv.ReportManagementView.as_view(), name='report_management'),
    path('reports/export/', ev.ReportExportView.as_view(), name='export_reports'),  

    path('rfid-dashboard/', rf.RFIDDashboardView.as_view(), name='rfid_dashboard'),
    path('rfid/issue/', rf.RFIDCardIssueView.as_view(), name='rfid_card_issue'),
    path('rfid/<int:pk>/edit/', rf.RFIDCardEditView.as_view(), name='edit_rfid_card'),
    path('rfid/export/', ev.RFIDCardExportView.as_view(), name='export_rfid_cards'),

    path('report-problem/', pr.ReportProblemView.as_view(), name='report_problem'),

    path('reminders/', rm.PhototherapyRemindersDashboardView.as_view(), name='reminders_dashboard'),
    path('reminders/create/', rm.CreatePhototherapyReminderView.as_view(), name='create_reminder'),
    path('reminders/send/', rm.send_reminder, name='send_reminder'),
    path('reminders/send-all/', rm.SendAllRemindersView.as_view(), name='send_all_reminders'),
    path('reminders/<int:reminder_id>/edit/', rm.edit_reminder, name='edit_reminder'),
    path('reminders/<int:pk>/delete/', rm.DeleteReminderView.as_view(), name='delete_reminder'),

    path('export/', ev.PhototherapyDashboardExportView.as_view(), name='phototherapy_export'),

    path('home-therapy/logs/', hv.HomeTherapyLogsView.as_view(), name='home_therapy_logs'),

    path('treatment-plan/<int:plan_id>/details/', 
         d.get_treatment_plan_details, 
         name='treatment_plan_details'),

    path('patient/<int:patient_id>/details/', 
         d.get_patient_details, 
         name='patient_details'),

    # Add these new payment-related URLs
    path('payments/', pmv.PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:payment_id>/', pmv.PaymentDetailView.as_view(), name='payment_detail'),

    # Add these new center-related URLs
    path('center/<int:center_id>/details/', 
         d.get_center_details, 
         name='center_details'),
]