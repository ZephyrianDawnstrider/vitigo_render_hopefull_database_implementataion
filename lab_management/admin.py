from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import LabTest, LabOrder, LabOrderItem, LabResult, LabReport, LabReportComment

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'description')

class LabOrderItemInline(admin.TabularInline):
    model = LabOrderItem
    extra = 1

class LabResultInline(admin.StackedInline):
    model = LabResult
    extra = 0
    can_delete = False

@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_link', 'order_date', 'status', 'ordered_by')
    list_filter = ('status', 'order_date')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'patient__user__email')
    inlines = [LabOrderItemInline]

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('lab_order_item', 'value', 'unit', 'status', 'performed_at', 'performed_by')
    list_filter = ('status', 'performed_at')
    search_fields = ('lab_order_item__lab_order__patient__user__first_name', 'lab_order_item__lab_order__patient__user__last_name', 'lab_order_item__lab_test__name')

class LabReportCommentInline(admin.TabularInline):
    model = LabReportComment
    extra = 1

@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display = ('lab_order', 'upload_type', 'uploaded_by', 'uploaded_at', 'is_sent_to_patient', 'report_file_link')
    list_filter = ('upload_type', 'uploaded_at', 'is_sent_to_patient')
    search_fields = ('lab_order__patient__user__first_name', 'lab_order__patient__user__last_name', 'lab_order__patient__user__email')
    inlines = [LabReportCommentInline]

    def report_file_link(self, obj):
        if obj.report_file:
            return format_html('<a href="{}" target="_blank">View Report</a>', obj.report_file.url)
        return "No file"
    report_file_link.short_description = 'Report File'

@admin.register(LabReportComment)
class LabReportCommentAdmin(admin.ModelAdmin):
    list_display = ('lab_report', 'created_by', 'created_at', 'comment_preview')
    list_filter = ('created_at',)
    search_fields = ('lab_report__lab_order__patient__user__first_name', 'lab_report__lab_order__patient__user__last_name', 'comment')

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment Preview'
