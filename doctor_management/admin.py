from django.contrib import admin
from .models import (
    Specialization,
    TreatmentMethodSpecialization,
    BodyAreaSpecialization,
    AssociatedConditionSpecialization,
    DoctorProfile,
    DoctorAvailability,
    DoctorReview
)

# Simple admin for specialization models
admin.site.register(Specialization)
admin.site.register(TreatmentMethodSpecialization)
admin.site.register(BodyAreaSpecialization)
admin.site.register(AssociatedConditionSpecialization)

# Basic DoctorProfile admin
@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'registration_number', 'qualification', 'experience', 'is_available')
    search_fields = ('user__email', 'registration_number')
    list_filter = ('is_available', 'experience')

# Basic DoctorAvailability admin
@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'shift', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'shift')

# Basic DoctorReview admin
@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'patient', 'rating', 'created_at')
    list_filter = ('rating',)
    readonly_fields = ('created_at', 'updated_at')
