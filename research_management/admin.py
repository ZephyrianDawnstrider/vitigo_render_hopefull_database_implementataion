from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    ResearchStudy, StudyProtocol, PatientStudyEnrollment,
    DataCollectionPoint, ResearchData, AnalysisResult, Publication
)

class StudyProtocolInline(admin.StackedInline):
    model = StudyProtocol
    extra = 0

class DataCollectionPointInline(admin.TabularInline):
    model = DataCollectionPoint
    extra = 1

@admin.register(ResearchStudy)
class ResearchStudyAdmin(admin.ModelAdmin):
    list_display = ('title', 'principal_investigator', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('title', 'description', 'principal_investigator__username')
    inlines = [StudyProtocolInline, DataCollectionPointInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'principal_investigator', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Documents', {
            'fields': ('ethics_approval_document',)
        }),
    )

@admin.register(PatientStudyEnrollment)
class PatientStudyEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'study_link', 'enrollment_date', 'status')
    list_filter = ('status', 'enrollment_date', 'study')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'study__title')

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())
    patient_link.short_description = 'Patient'

    def study_link(self, obj):
        url = reverse("admin:research_management_researchstudy_change", args=[obj.study.id])
        return format_html('<a href="{}">{}</a>', url, obj.study.title)
    study_link.short_description = 'Study'

@admin.register(ResearchData)
class ResearchDataAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'collection_point', 'collected_date', 'collected_by')
    list_filter = ('collected_date', 'collection_point__study')
    search_fields = ('enrollment__patient__user__first_name', 'enrollment__patient__user__last_name', 'collection_point__name')

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('title', 'study', 'created_by', 'created_at')
    list_filter = ('created_at', 'study')
    search_fields = ('title', 'description', 'study__title')

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'study', 'journal', 'publication_date')
    list_filter = ('publication_date', 'journal')
    search_fields = ('title', 'authors', 'study__title')

# Registering the remaining models
admin.site.register(StudyProtocol)
admin.site.register(DataCollectionPoint)
