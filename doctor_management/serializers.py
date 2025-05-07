# serializers.py
from rest_framework import serializers
from user_management.models import CustomUser
from doctor_management.models import (
    DoctorProfile, Specialization, TreatmentMethodSpecialization,
    BodyAreaSpecialization, AssociatedConditionSpecialization,
    DoctorAvailability, DoctorReview
)

class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'profile_picture']

class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ['id', 'name', 'description']

class TreatmentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentMethodSpecialization
        fields = ['id', 'name', 'description']

class BodyAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyAreaSpecialization
        fields = ['id', 'name', 'description']

class AssociatedConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssociatedConditionSpecialization
        fields = ['id', 'name', 'description']

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DoctorAvailability
        fields = ['id', 'day_of_week', 'day_name', 'shift', 'start_time', 'end_time', 'is_available']

class DoctorReviewSerializer(serializers.ModelSerializer):
    patient = BasicUserSerializer(read_only=True)
    
    class Meta:
        model = DoctorReview
        fields = ['id', 'patient', 'rating', 'review', 'created_at']

class DoctorListSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'qualification', 'experience',
            'specializations', 'consultation_fee', 'city',
            'state', 'rating', 'is_available'
        ]

class DoctorDetailSerializer(serializers.ModelSerializer):
    user = BasicUserSerializer(read_only=True)
    specializations = SpecializationSerializer(many=True, read_only=True)
    treatment_methods = TreatmentMethodSerializer(many=True, read_only=True)
    body_areas = BodyAreaSerializer(many=True, read_only=True)
    associated_conditions = AssociatedConditionSerializer(many=True, read_only=True)
    availability = DoctorAvailabilitySerializer(many=True, read_only=True)
    reviews = DoctorReviewSerializer(many=True, read_only=True)
    
    class Meta:
        model = DoctorProfile
        fields = [
            'id', 'user', 'registration_number', 'qualification',
            'experience', 'specializations', 'treatment_methods',
            'body_areas', 'associated_conditions', 'consultation_fee',
            'about', 'address', 'city', 'state', 'country',
            'rating', 'is_available', 'availability', 'reviews',
            'created_at', 'updated_at'
        ]