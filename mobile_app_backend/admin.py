from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import MobileDeviceToken, PatientEducationMaterial, MobileAppointmentRequest, PatientQuery, PatientQueryResponse, MobileNotification

@admin.register(MobileDeviceToken)
class MobileDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'last_used')
    list_filter = ('device_type', 'is_active', 'last_used')
    search_fields = ('user__email', 'device_token')
    readonly_fields = ('last_used',)

@admin.register(PatientEducationMaterial)
class PatientEducationMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at', 'updated_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')
    actions = ['publish_materials', 'unpublish_materials']

    def publish_materials(self, request, queryset):
        queryset.update(is_published=True)
    publish_materials.short_description = "Publish selected materials"

    def unpublish_materials(self, request, queryset):
        queryset.update(is_published=False)
    unpublish_materials.short_description = "Unpublish selected materials"

@admin.register(MobileAppointmentRequest)
class MobileAppointmentRequestAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'preferred_date', 'preferred_time', 'status', 'created_at')
    list_filter = ('status', 'preferred_date', 'created_at')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'patient__user__email', 'reason')
    readonly_fields = ('created_at', 'updated_at')

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

class PatientQueryResponseInline(admin.TabularInline):
    model = PatientQueryResponse
    extra = 1

@admin.register(PatientQuery)
class PatientQueryAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'patient__user__email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PatientQueryResponseInline]

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

@admin.register(MobileNotification)
class MobileNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'title', 'message')
    readonly_fields = ('created_at',)
