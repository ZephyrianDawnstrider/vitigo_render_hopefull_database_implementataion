from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    TeleconsultationSession, TeleconsultationPrescription,
    TeleconsultationFile, TeleconsultationFeedback, TelemedicinevirtualWaitingRoom
)

class TeleconsultationPrescriptionInline(admin.StackedInline):
    model = TeleconsultationPrescription
    extra = 0

class TeleconsultationFileInline(admin.TabularInline):
    model = TeleconsultationFile
    extra = 1

class TeleconsultationFeedbackInline(admin.StackedInline):
    model = TeleconsultationFeedback
    extra = 0

@admin.register(TeleconsultationSession)
class TeleconsultationSessionAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'doctor_link', 'scheduled_start', 'status', 'is_recorded')
    list_filter = ('status', 'scheduled_start', 'is_recorded')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'doctor__first_name', 'doctor__last_name')
    inlines = [TeleconsultationPrescriptionInline, TeleconsultationFileInline, TeleconsultationFeedbackInline]

    fieldsets = (
        (None, {
            'fields': ('patient', 'doctor', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_start', 'scheduled_end', 'actual_start', 'actual_end')
        }),
        ('Video Call', {
            'fields': ('video_call_link', 'is_recorded', 'recording_url')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
    )

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

    def doctor_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.doctor.id])
        return format_html('<a href="{}">{}</a>', url, obj.doctor.get_full_name())
    doctor_link.short_description = 'Doctor'

@admin.register(TeleconsultationFile)
class TeleconsultationFileAdmin(admin.ModelAdmin):
    list_display = ('teleconsultation', 'file_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type', 'uploaded_at')
    search_fields = ('teleconsultation__patient__user__first_name', 'teleconsultation__patient__user__last_name', 'description')

@admin.register(TeleconsultationFeedback)
class TeleconsultationFeedbackAdmin(admin.ModelAdmin):
    list_display = ('teleconsultation', 'rating', 'submitted_by', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
    search_fields = ('teleconsultation__patient__user__first_name', 'teleconsultation__patient__user__last_name', 'comments')

@admin.register(TelemedicinevirtualWaitingRoom)
class TelemedicinevirtualWaitingRoomAdmin(admin.ModelAdmin):
    list_display = ('patient', 'teleconsultation', 'joined_at', 'is_active')
    list_filter = ('is_active', 'joined_at')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'teleconsultation__doctor__first_name', 'teleconsultation__doctor__last_name')
