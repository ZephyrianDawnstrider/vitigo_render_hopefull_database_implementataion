from django.contrib import admin
from .models import (
    VisitStatus, ClinicVisit, VisitStatusLog,
    ClinicChecklist, ChecklistItem, VisitChecklist,
    VisitChecklistItem
)

@admin.register(VisitStatus)
class VisitStatusAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'is_active', 'is_terminal_state', 'order')
    search_fields = ('name', 'display_name')
    list_filter = ('is_active', 'is_terminal_state')

@admin.register(ClinicVisit)
class ClinicVisitAdmin(admin.ModelAdmin):
    list_display = ('visit_number', 'patient', 'visit_date', 'current_status', 'priority')
    search_fields = ('visit_number', 'patient__first_name', 'patient__last_name')
    list_filter = ('priority', 'visit_date', 'current_status')
    date_hierarchy = 'visit_date'

@admin.register(VisitStatusLog)
class VisitStatusLogAdmin(admin.ModelAdmin):
    list_display = ('visit', 'status', 'timestamp', 'changed_by')
    search_fields = ('visit__visit_number', 'status__name')
    list_filter = ('status', 'timestamp')

@admin.register(ClinicChecklist)
class ClinicChecklistAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('description', 'checklist', 'order', 'is_required')
    search_fields = ('description', 'checklist__name')
    list_filter = ('is_required', 'checklist')

@admin.register(VisitChecklist)
class VisitChecklistAdmin(admin.ModelAdmin):
    list_display = ('visit', 'checklist', 'completed_by', 'completed_at')
    search_fields = ('visit__visit_number', 'checklist__name')
    list_filter = ('completed_at', 'checklist')

@admin.register(VisitChecklistItem)
class VisitChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('visit_checklist', 'checklist_item', 'is_completed', 'completed_at')
    search_fields = ('visit_checklist__visit__visit_number', 'checklist_item__description')
    list_filter = ('is_completed', 'completed_at')
