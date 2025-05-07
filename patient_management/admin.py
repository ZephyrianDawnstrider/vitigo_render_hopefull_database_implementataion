from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Patient, MedicalHistory, Medication, VitiligoAssessment, TreatmentPlan


class MedicalHistoryInline(admin.StackedInline):
    model = MedicalHistory
    can_delete = False
    verbose_name_plural = 'Medical History'


class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 1


class VitiligoAssessmentInline(admin.TabularInline):
    model = VitiligoAssessment
    extra = 1


class TreatmentPlanInline(admin.StackedInline):
    model = TreatmentPlan
    extra = 1


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number', 'date_of_birth', 'vitiligo_onset_date')
    list_filter = ('gender', 'blood_group', 'vitiligo_type')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone_number')
    inlines = [MedicalHistoryInline, MedicationInline, VitiligoAssessmentInline, TreatmentPlanInline]

    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'date_of_birth', 'gender', 'blood_group', 'address', 'phone_number')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_number')
        }),
        ('Vitiligo Information', {
            'fields': ('vitiligo_onset_date', 'vitiligo_type', 'affected_body_areas')
        }),
    )

    def full_name(self, obj):
        return obj.user.get_full_name()

    full_name.short_description = 'Full Name'

    def email(self, obj):
        return obj.user.email

    email.short_description = 'Email'


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'patient_link', 'dosage', 'frequency', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('name', 'patient__user__first_name', 'patient__user__last_name', 'patient__user__email')

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())

    patient_link.short_description = 'Patient'


@admin.register(VitiligoAssessment)
class VitiligoAssessmentAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'assessment_date', 'body_surface_area_affected', 'vasi_score')
    list_filter = ('assessment_date',)
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'patient__user__email')

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())

    patient_link.short_description = 'Patient'


@admin.register(TreatmentPlan)
class TreatmentPlanAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'created_date', 'updated_date', 'follow_up_frequency')
    list_filter = ('created_date', 'updated_date')
    search_fields = ('patient__user__first_name', 'patient__user__last_name', 'patient__user__email', 'treatment_goals')
    filter_horizontal = ('medications',)

    def patient_link(self, obj):
        url = reverse("admin:patient_management_patient_change", args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.user.get_full_name())

    patient_link.short_description = 'Patient'