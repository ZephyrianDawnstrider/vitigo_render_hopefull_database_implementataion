from django.contrib import admin
from .models import (
    ProcedureCategory,
    ProcedureType,
    ProcedurePrerequisite,
    ProcedureInstruction,
    Procedure,
    ConsentForm,
    ProcedureChecklistTemplate,
    ChecklistItem,
    ProcedureChecklist,
    CompletedChecklistItem,
    ProcedureMedia
)

@admin.register(ProcedureCategory)
class ProcedureCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')

@admin.register(ProcedureType)
class ProcedureTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'duration_minutes', 'base_cost', 'priority', 'is_active')
    list_filter = ('category', 'priority', 'is_active', 'requires_consent', 'requires_fasting')
    search_fields = ('name', 'code', 'description')

@admin.register(ProcedurePrerequisite)
class ProcedurePrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('procedure_type', 'name', 'is_mandatory', 'order')
    list_filter = ('is_mandatory', 'procedure_type')
    search_fields = ('name', 'description')

@admin.register(ProcedureInstruction)
class ProcedureInstructionAdmin(admin.ModelAdmin):
    list_display = ('procedure_type', 'instruction_type', 'title', 'order', 'is_active')
    list_filter = ('instruction_type', 'is_active', 'procedure_type')
    search_fields = ('title', 'description')

@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ('procedure_type', 'patient', 'scheduled_date', 'status', 'primary_doctor')
    list_filter = ('status', 'payment_status', 'scheduled_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'procedure_type__name', 'notes')
    date_hierarchy = 'scheduled_date'

@admin.register(ConsentForm)
class ConsentFormAdmin(admin.ModelAdmin):
    list_display = ('procedure', 'signed_by_patient', 'signed_datetime', 'witness_name')
    list_filter = ('signed_by_patient',)
    search_fields = ('procedure__patient__first_name', 'procedure__patient__last_name', 'witness_name')

@admin.register(ProcedureChecklistTemplate)
class ProcedureChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'procedure_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'procedure_type')
    search_fields = ('name', 'description')

@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('template', 'description', 'is_mandatory', 'order')
    list_filter = ('is_mandatory', 'template')
    search_fields = ('description',)

@admin.register(ProcedureChecklist)
class ProcedureChecklistAdmin(admin.ModelAdmin):
    list_display = ('procedure', 'template', 'completed_by', 'completed_at')
    list_filter = ('template', 'completed_at')
    search_fields = ('procedure__patient__first_name', 'procedure__patient__last_name', 'notes')

@admin.register(CompletedChecklistItem)
class CompletedChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('checklist', 'item', 'is_completed', 'completed_by', 'completed_at')
    list_filter = ('is_completed',)
    search_fields = ('notes', 'item__description')

@admin.register(ProcedureMedia)
class ProcedureMediaAdmin(admin.ModelAdmin):
    list_display = ('procedure', 'title', 'file_type', 'uploaded_by', 'uploaded_at', 'is_private')
    list_filter = ('file_type', 'is_private', 'uploaded_at')
    search_fields = ('title', 'description', 'procedure__patient__first_name', 'procedure__patient__last_name')
