from django.contrib import admin
from .models import (
    PhototherapyType, PatientRFIDCard, PhototherapyDevice,
    PhototherapyProtocol, PhototherapyPackage, PhototherapyPlan, 
    PhototherapySession, HomePhototherapyLog, ProblemReport, 
    PhototherapyPayment, PhototherapyReminder, PhototherapyProgress, 
    DeviceMaintenance
)

@admin.register(PhototherapyType)
class PhototherapyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'therapy_type', 'priority', 'is_active')
    list_filter = ('therapy_type', 'priority', 'is_active')
    search_fields = ('name', 'description')

@admin.register(PatientRFIDCard)
class PatientRFIDCardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'patient', 'is_active', 'expires_at')
    list_filter = ('is_active',)
    search_fields = ('card_number', 'patient__first_name', 'patient__last_name')

@admin.register(PhototherapyDevice)
class PhototherapyDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'phototherapy_type', 'location', 'is_active')
    list_filter = ('phototherapy_type', 'is_active')
    search_fields = ('name', 'serial_number', 'model_number')

@admin.register(PhototherapyProtocol)
class PhototherapyProtocolAdmin(admin.ModelAdmin):
    list_display = ('name', 'phototherapy_type', 'initial_dose', 'max_dose', 'is_active')
    list_filter = ('phototherapy_type', 'is_active')
    search_fields = ('name', 'description')

@admin.register(PhototherapyPlan)
class PhototherapyPlanAdmin(admin.ModelAdmin):
    list_display = ('patient', 'protocol', 'start_date', 'billing_status', 'is_active')
    list_filter = ('billing_status', 'is_active')
    search_fields = ('patient__first_name', 'patient__last_name')

@admin.register(PhototherapySession)
class PhototherapySessionAdmin(admin.ModelAdmin):
    list_display = ('session_number', 'plan', 'scheduled_date', 'status')
    list_filter = ('status', 'problem_severity')
    search_fields = ('plan__patient__first_name', 'plan__patient__last_name')

@admin.register(HomePhototherapyLog)
class HomePhototherapyLogAdmin(admin.ModelAdmin):
    list_display = ('plan', 'date', 'exposure_type', 'duration_minutes')
    list_filter = ('exposure_type',)
    search_fields = ('plan__patient__first_name', 'plan__patient__last_name')

@admin.register(ProblemReport)
class ProblemReportAdmin(admin.ModelAdmin):
    list_display = ('session', 'severity', 'resolved', 'reported_at')
    list_filter = ('severity', 'resolved')
    search_fields = ('problem_description',)

@admin.register(PhototherapyPayment)
class PhototherapyPaymentAdmin(admin.ModelAdmin):
    list_display = ('plan', 'amount', 'payment_date', 'status', 'payment_method')
    list_filter = ('status', 'payment_method')
    search_fields = ('receipt_number', 'transaction_id')

@admin.register(PhototherapyReminder)
class PhototherapyReminderAdmin(admin.ModelAdmin):
    list_display = ('plan', 'reminder_type', 'scheduled_datetime', 'status')
    list_filter = ('reminder_type', 'status')
    search_fields = ('message',)

@admin.register(PhototherapyProgress)
class PhototherapyProgressAdmin(admin.ModelAdmin):
    list_display = ('plan', 'assessment_date', 'response_level', 'improvement_percentage')
    list_filter = ('response_level',)
    search_fields = ('notes',)

@admin.register(DeviceMaintenance)
class DeviceMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('device', 'maintenance_type', 'maintenance_date', 'next_maintenance_due')
    list_filter = ('maintenance_type',)
    search_fields = ('device__name', 'device__serial_number')

@admin.register(PhototherapyPackage)
class PhototherapyPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'therapy_type', 'number_of_sessions', 'total_cost', 'is_featured', 'is_active')
    list_filter = ('is_featured', 'is_active', 'therapy_type')
    search_fields = ('name', 'description')
