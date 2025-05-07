from django.contrib import admin
from .models import (
    ComplianceSchedule,
    ComplianceNote,
    ComplianceIssue,
    ComplianceMetric,
    ComplianceReminder,
    ComplianceReport,
    PatientGroup,
    ComplianceAlert
)

@admin.register(ComplianceSchedule)
class ComplianceScheduleAdmin(admin.ModelAdmin):
    list_display = ('patient', 'scheduled_date', 'scheduled_time', 'status', 'priority')
    list_filter = ('status', 'priority')
    search_fields = ('patient__first_name', 'patient__last_name')
    date_hierarchy = 'scheduled_date'

@admin.register(ComplianceNote)
class ComplianceNoteAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'note_type', 'created_by', 'created_at', 'is_private')
    list_filter = ('note_type', 'is_private')
    search_fields = ('content',)

@admin.register(ComplianceIssue)
class ComplianceIssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'patient', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status')
    search_fields = ('title', 'description', 'patient__first_name', 'patient__last_name')

@admin.register(ComplianceMetric)
class ComplianceMetricAdmin(admin.ModelAdmin):
    list_display = ('patient', 'metric_type', 'compliance_score', 'evaluation_date')
    list_filter = ('metric_type',)
    search_fields = ('patient__first_name', 'patient__last_name')

@admin.register(ComplianceReminder)
class ComplianceReminderAdmin(admin.ModelAdmin):
    list_display = ('patient', 'reminder_type', 'scheduled_datetime', 'status')
    list_filter = ('reminder_type', 'status')
    search_fields = ('patient__first_name', 'patient__last_name', 'message')

@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'generated_by', 'generated_at')
    list_filter = ('report_type',)
    search_fields = ('title', 'description')

@admin.register(PatientGroup)
class PatientGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

@admin.register(ComplianceAlert)
class ComplianceAlertAdmin(admin.ModelAdmin):
    list_display = ('patient', 'alert_type', 'severity', 'is_resolved', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_resolved')
    search_fields = ('patient__first_name', 'patient__last_name', 'message')
