from django.contrib import admin
from .models import (
    TimeSlotConfig,
    DoctorTimeSlot,
    Appointment,
    ReminderTemplate,
    ReminderConfiguration,
    AppointmentReminder,
    CancellationReason,
    AppointmentAcknowledgement  # Add this import
)

@admin.register(TimeSlotConfig)
class TimeSlotConfigAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'duration', 'is_active')
    list_filter = ('is_active',)

@admin.register(DoctorTimeSlot)
class DoctorTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'date', 'start_time', 'end_time', 'is_available')
    list_filter = ('date', 'is_available', 'doctor')
    search_fields = ('doctor__username', 'doctor__email')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'appointment_type', 'status', 'priority')
    list_filter = ('status', 'appointment_type', 'priority')
    search_fields = ('patient__username', 'doctor__username')

@admin.register(ReminderTemplate)
class ReminderTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'days_before', 'hours_before', 'is_active')
    list_filter = ('is_active',)

@admin.register(ReminderConfiguration)
class ReminderConfigurationAdmin(admin.ModelAdmin):
    list_display = ('appointment_type', 'is_active')
    list_filter = ('is_active',)

@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'reminder_type', 'status', 'reminder_date', 'sent')
    list_filter = ('status', 'reminder_type', 'sent')

@admin.register(CancellationReason)
class CancellationReasonAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'cancelled_by', 'cancelled_at')
    search_fields = ('appointment__patient__username', 'reason')

@admin.register(AppointmentAcknowledgement)
class AppointmentAcknowledgementAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'user', 'acknowledged_at')
    list_filter = ('acknowledged_at', 'user')
