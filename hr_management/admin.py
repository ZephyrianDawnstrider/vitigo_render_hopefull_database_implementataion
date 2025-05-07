from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Department, Position, Employee, Attendance, Leave,
    PayrollPeriod, Payroll, PerformanceReview, Training,
    TrainingParticipant, Document, Grievance, AssetAssignment,
    EmployeeSkill
)

# Simple admin classes for all models
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'min_salary', 'max_salary', 'is_active')
    search_fields = ('title', 'department__name')
    list_filter = ('department', 'is_active')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'position', 'employment_status')
    search_fields = ('employee_id', 'user__username', 'user__first_name', 'user__last_name')
    list_filter = ('department', 'employment_status', 'is_active')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'date')
    search_fields = ('employee__employee_id', 'employee__user__username')

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status')
    search_fields = ('employee__employee_id', 'employee__user__username')

@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'is_processed', 'processed_at')
    list_filter = ('is_processed',)

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'period', 'basic_salary', 'net_salary', 'payment_status')
    list_filter = ('payment_status', 'period')
    search_fields = ('employee__employee_id', 'employee__user__username')

@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ('employee', 'reviewer', 'review_date', 'status')
    list_filter = ('status', 'review_date')
    search_fields = ('employee__employee_id', 'employee__user__username')

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ('title', 'trainer', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
    search_fields = ('title', 'trainer')

@admin.register(TrainingParticipant)
class TrainingParticipantAdmin(admin.ModelAdmin):
    list_display = ('training', 'employee', 'status', 'score')
    list_filter = ('status', 'training')
    search_fields = ('employee__employee_id', 'employee__user__username')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'title', 'is_verified')
    list_filter = ('document_type', 'is_verified')
    search_fields = ('employee__employee_id', 'title')

@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'subject', 'priority', 'status', 'filed_date')
    list_filter = ('priority', 'status')
    search_fields = ('employee__employee_id', 'subject')

@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'asset_type', 'asset_id', 'assigned_date')
    list_filter = ('asset_type',)
    search_fields = ('employee__employee_id', 'asset_id')

@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('employee', 'skill_name', 'proficiency_level', 'is_primary')
    list_filter = ('is_primary', 'certified')
    search_fields = ('employee__employee_id', 'skill_name')