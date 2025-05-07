from django.contrib import admin
from .models import (
    Consultation, DoctorPrivateNotes, PrescriptionTemplate, TemplateItem,
    Prescription, PrescriptionItem, TreatmentPlan, TreatmentPlanItem,
    StaffInstruction, ConsultationPhototherapy, ConsultationAttachment
)

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_datetime', 'consultation_type', 'status')
    list_filter = ('status', 'consultation_type', 'priority')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__first_name')

@admin.register(DoctorPrivateNotes)
class DoctorPrivateNotesAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'created_at', 'updated_at')

@admin.register(PrescriptionTemplate)
class PrescriptionTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'doctor', 'is_global', 'is_active')
    list_filter = ('is_global', 'is_active')

@admin.register(TemplateItem)
class TemplateItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'medication', 'dosage', 'order')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'template_used', 'created_at')
    search_fields = ('consultation__patient__first_name', 'consultation__patient__last_name')

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'medication', 'dosage', 'quantity_prescribed')

@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'duration_weeks', 'total_cost', 'payment_status')
    list_filter = ('payment_status',)

@admin.register(TreatmentPlanItem)
class TreatmentPlanItemAdmin(admin.ModelAdmin):
    list_display = ('treatment_plan', 'name', 'cost', 'order')

@admin.register(StaffInstruction)
class StaffInstructionAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'priority', 'created_at')
    list_filter = ('priority',)

@admin.register(ConsultationPhototherapy)
class ConsultationPhototherapyAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'phototherapy_session', 'schedule')
    list_filter = ('schedule',)

@admin.register(ConsultationAttachment)
class ConsultationAttachmentAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'title', 'file_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('file_type',)
    search_fields = ('title', 'description')
