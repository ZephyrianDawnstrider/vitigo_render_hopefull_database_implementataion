from rest_framework import serializers
from .models import Patient, MedicalHistory, Medication, VitiligoAssessment, TreatmentPlan
from user_management.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from datetime import date
from django.utils import timezone

User = get_user_model()

class PatientSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'user', 'date_of_birth', 'gender', 'blood_group', 'address', 'phone_number',
                  'emergency_contact_name', 'emergency_contact_number', 'vitiligo_onset_date',
                  'vitiligo_type', 'affected_body_areas', 'created_at', 'updated_at']

class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = ['id', 'allergies', 'chronic_conditions', 'past_surgeries', 'family_history']

class MedicationSerializer(serializers.ModelSerializer):
    prescribed_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = Medication
        fields = ['id', 'name', 'dosage', 'frequency', 'start_date', 'end_date', 'prescribed_by']

class VitiligoAssessmentSerializer(serializers.ModelSerializer):
    assessed_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = VitiligoAssessment
        fields = ['id', 'assessment_date', 'body_surface_area_affected', 'vasi_score',
                  'treatment_response', 'notes', 'assessed_by']

class TreatmentPlanSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    medications = MedicationSerializer(many=True, read_only=True)

    class Meta:
        model = TreatmentPlan
        fields = ['id', 'created_date', 'updated_date', 'treatment_goals', 'medications',
                  'phototherapy_details', 'lifestyle_recommendations', 'follow_up_frequency',
                  'created_by']
        

class PatientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'date_of_birth',
            'gender',
            'blood_group',
            'address',
            'phone_number',
            'emergency_contact_name',
            'emergency_contact_number',
            'vitiligo_onset_date',
            'vitiligo_type',
            'affected_body_areas'
        ]

class MedicalHistoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = [
            'allergies',
            'chronic_conditions',
            'past_surgeries',
            'family_history'
        ]

class PatientUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'date_of_birth',
            'gender',
            'blood_group',
            'address',
            'phone_number',
            'emergency_contact_name',
            'emergency_contact_number',
            'vitiligo_onset_date',
            'vitiligo_type',
            'affected_body_areas'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_date_of_birth(self, value):
        """
        Validate that date of birth is not in the future and not too far in the past
        """
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        if value.year < 1900:
            raise serializers.ValidationError("Please enter a valid date of birth")
        return value

    def validate_gender(self, value):
        """
        Validate gender is one of the allowed choices
        """
        valid_choices = dict(Patient.GENDER_CHOICES)
        if value not in valid_choices:
            raise serializers.ValidationError(f"Gender must be one of: {', '.join(valid_choices.keys())}")
        return value

    def validate_blood_group(self, value):
        """
        Validate blood group is one of the allowed choices
        """
        if value:  # Allow null/blank values as per model
            valid_choices = dict(Patient.BLOOD_GROUP_CHOICES)
            if value not in valid_choices:
                raise serializers.ValidationError(f"Blood group must be one of: {', '.join(valid_choices.keys())}")
        return value

    def validate_phone_number(self, value):
        """
        Validate phone number format and length
        """
        # Remove any spaces or special characters
        cleaned_number = ''.join(filter(str.isdigit, value))
        
        if not cleaned_number.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits")
        
        if len(cleaned_number) < 10 or len(cleaned_number) > 15:
            raise serializers.ValidationError("Phone number must be between 10 and 15 digits")
        
        return cleaned_number

    def validate_emergency_contact_number(self, value):
        """
        Validate emergency contact number format and length
        """
        # Remove any spaces or special characters
        cleaned_number = ''.join(filter(str.isdigit, value))
        
        if not cleaned_number.isdigit():
            raise serializers.ValidationError("Emergency contact number must contain only digits")
        
        if len(cleaned_number) < 10 or len(cleaned_number) > 15:
            raise serializers.ValidationError("Emergency contact number must be between 10 and 15 digits")
        
        return cleaned_number

    def validate_emergency_contact_name(self, value):
        """
        Validate emergency contact name
        """
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Emergency contact name is too short")
        if len(value) > 100:
            raise serializers.ValidationError("Emergency contact name is too long")
        return value.strip()

    def validate_vitiligo_onset_date(self, value):
        """
        Validate vitiligo onset date
        """
        if value:  # Allow null values as per model
            if value > date.today():
                raise serializers.ValidationError("Vitiligo onset date cannot be in the future")
            if value.year < 1900:
                raise serializers.ValidationError("Please enter a valid onset date")
        return value

    def validate_address(self, value):
        """
        Validate address
        """
        if value:
            if len(value.strip()) < 5:
                raise serializers.ValidationError("Address is too short")
            if len(value) > 500:
                raise serializers.ValidationError("Address is too long")
        return value.strip()

    def validate(self, data):
        """
        Cross-field validation
        """
        # Check if onset date is after date of birth
        if 'vitiligo_onset_date' in data and 'date_of_birth' in data:
            if data['vitiligo_onset_date'] and data['date_of_birth']:
                if data['vitiligo_onset_date'] < data['date_of_birth']:
                    raise serializers.ValidationError({
                        'vitiligo_onset_date': 'Vitiligo onset date cannot be before date of birth'
                    })

        # Ensure emergency contact number is different from patient's phone number
        if 'phone_number' in data and 'emergency_contact_number' in data:
            if data['phone_number'] == data['emergency_contact_number']:
                raise serializers.ValidationError({
                    'emergency_contact_number': 'Emergency contact number cannot be the same as your phone number'
                })

        return data

    def update(self, instance, validated_data):
        """
        Update and return an existing Patient instance
        """
        instance = super().update(instance, validated_data)
        instance.updated_at = timezone.now()
        instance.save()
        return instance

class MedicalHistoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = [
            'allergies',
            'chronic_conditions',
            'past_surgeries',
            'family_history'
        ]
        read_only_fields = ['patient']

    def validate_allergies(self, value):
        """
        Validate allergies field
        """
        if value:
            if len(value.strip()) < 2 and len(value.strip()) > 0:
                raise serializers.ValidationError("Allergies description is too short")
            if len(value) > 1000:
                raise serializers.ValidationError("Allergies description is too long")
        return value.strip() if value else value

    def validate_chronic_conditions(self, value):
        """
        Validate chronic conditions field
        """
        if value:
            if len(value.strip()) < 2 and len(value.strip()) > 0:
                raise serializers.ValidationError("Chronic conditions description is too short")
            if len(value) > 1000:
                raise serializers.ValidationError("Chronic conditions description is too long")
        return value.strip() if value else value

    def validate_past_surgeries(self, value):
        """
        Validate past surgeries field
        """
        if value:
            if len(value.strip()) < 2 and len(value.strip()) > 0:
                raise serializers.ValidationError("Past surgeries description is too short")
            if len(value) > 1000:
                raise serializers.ValidationError("Past surgeries description is too long")
        return value.strip() if value else value

    def validate_family_history(self, value):
        """
        Validate family history field
        """
        if value:
            if len(value.strip()) < 2 and len(value.strip()) > 0:
                raise serializers.ValidationError("Family history description is too short")
            if len(value) > 1000:
                raise serializers.ValidationError("Family history description is too long")
        return value.strip() if value else value

    def validate(self, data):
        """
        Cross-field validation if needed
        """
        # Add any cross-field validation logic here if required
        return data

    def update(self, instance, validated_data):
        """
        Update and return an existing MedicalHistory instance
        """
        # Update each field if it's present in validated_data
        for field in self.Meta.fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance