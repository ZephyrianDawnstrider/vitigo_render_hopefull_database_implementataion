from django.urls import path
from .views import (
    appointments as appointment_views,
    dashboard as dashboard_views,
    exports as export_views,
    reminders as reminder_views,
)
from .views.calendar import AppointmentCalendarView
from .views.timeslots import (
    DoctorTimeSlotDashboardView,
    DoctorTimeSlotsView,
    DoctorTimeSlotCreateView,
    DoctorTimeSlotUpdateView,
    DoctorTimeSlotDeleteView,
)

# URL patterns grouped by functionality
urlpatterns = [
    # Dashboard URLs
    path('', dashboard_views.AppointmentDashboardView.as_view(), 
         name='appointment_dashboard'),

    # Appointment Management URLs
    path('<int:pk>/', appointment_views.AppointmentDetailView.as_view(), 
         name='appointment_detail'),
    path('create/', appointment_views.AppointmentCreateView.as_view(), 
         name='appointment_create'),
    path('<int:appointment_id>/status/', 
         appointment_views.update_appointment_status, 
         name='update_appointment_status'),
    path('<int:appointment_id>/delete/', 
         appointment_views.AppointmentDeleteView.as_view(), 
         name='appointment_delete'),
    path('<int:appointment_id>/reschedule/', 
         appointment_views.AppointmentRescheduleView.as_view(), 
         name='appointment_reschedule'),
    path('<int:appointment_id>/acknowledge/', 
         appointment_views.acknowledge_appointment, 
         name='acknowledge_appointment'),

    # Export URLs
    path('export/', export_views.AppointmentExportView.as_view(), 
         name='appointment_export'),
    path('export/<int:appointment_id>/', 
         export_views.AppointmentExportSingleView.as_view(), 
         name='appointment_export_single'),

    # Reminder Management URLs
    path('reminders/', reminder_views.AppointmentReminderView.as_view(), 
         name='appointment_reminders'),
    path('reminders/create-template/', 
         reminder_views.CreateReminderTemplateView.as_view(), 
         name='create_reminder_template'),
    path('reminders/configure/', 
         reminder_views.ConfigureReminderSettingsView.as_view(), 
         name='configure_reminder_settings'),
    path('reminders/delete-template/<int:template_id>/', 
         reminder_views.DeleteReminderTemplateView.as_view(), 
         name='delete_reminder_template'),
    path('reminders/delete-config/<int:config_id>/', 
         reminder_views.DeleteReminderConfigurationView.as_view(), 
         name='delete_reminder_config'),
    path('reminders/edit-template/<int:template_id>/', 
         reminder_views.EditReminderTemplateView.as_view(), 
         name='edit_reminder_template'),
    path('reminders/edit-config/<int:config_id>/', 
         reminder_views.EditReminderConfigurationView.as_view(), 
         name='edit_reminder_config'),

    # Calendar URL
    path('calendar/', AppointmentCalendarView.as_view(), name='appointment_calendar'),

    # Time Slot Management URLs - Reorganized
    path('timeslots/', DoctorTimeSlotDashboardView.as_view(), name='timeslot_dashboard'),
    path('timeslots/<int:pk>/', DoctorTimeSlotsView.as_view(), name='doctor_timeslots'),
    path('timeslots/create/', DoctorTimeSlotCreateView.as_view(), name='timeslot_create'),
    path('timeslots/slot/<int:pk>/edit/', DoctorTimeSlotUpdateView.as_view(), name='timeslot_update'),
    path('timeslots/slot/<int:pk>/delete/', DoctorTimeSlotDeleteView.as_view(), name='timeslot_delete'),

    # Add this new URL pattern for doctor timeslots
    path('doctor-timeslots/', appointment_views.get_doctor_timeslots, name='get_doctor_timeslots'),
    path('doctor-centers/', appointment_views.get_doctor_centers, name='get_doctor_centers'),
    path('doctor-available-dates/', appointment_views.get_doctor_available_dates, name='get_doctor_available_dates'),
]