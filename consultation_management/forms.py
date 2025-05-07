# consultation_management/forms.py
from django import forms
from django.core.exceptions import ValidationError
import logging
from django.utils import timezone
from django_select2.forms import Select2Widget

from .models import Consultation, ConsultationType, ConsultationPriority
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

class ConsultationForm(forms.ModelForm):
    urgent_consultation = forms.BooleanField(
        required=False,
        label="Urgent Consultation Request (serious cases only)"
    )

    DURATION_CHOICES = [
        (15, '15 minutes'),
        (30, '30 minutes'),
        (45, '45 minutes'),
    ]

    duration_minutes = forms.ChoiceField(
        choices=DURATION_CHOICES,
        initial='30',
        help_text="Default consultation duration is 30 minutes"
    )

    from appointment_management.models import Center, DoctorTimeSlot

    center = forms.ModelChoiceField(
        queryset=Center.objects.filter(is_active=True),
        required=True,
        label="Medical Center",
        widget=Select2Widget
    )

    time_slot = forms.ModelChoiceField(
        queryset=DoctorTimeSlot.objects.none(),
        required=True,
        label="Available Time Slot"
    )

    class Meta:
        model = Consultation
        fields = [
            'patient', 'doctor', 'consultation_type', 'priority',
            'scheduled_datetime', 'chief_complaint', 'duration_minutes',
            'center', 'time_slot'
        ]
        widgets = {
            'patient': Select2Widget,
            'doctor': Select2Widget,
            'scheduled_datetime': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'chief_complaint': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        try:
            # Filter patient choices to only show patients
            self.fields['patient'].queryset = User.objects.filter(
                role__name='PATIENT'
            )
            
            # Filter doctor choices to only show doctors
            self.fields['doctor'].queryset = User.objects.filter(
                role__name='DOCTOR'
            )
            
            # If the user is a doctor, pre-select the doctor field but do not disable it
            if user and user.role.name == 'DOCTOR':
                self.fields['doctor'].initial = user
                # Do not disable the doctor field to allow selection of other doctors

            # elif user and user.role.name != 'ADMINISTRATOR':
            #     # Hide doctor field for non-admin, non-doctor users
            #     self.fields.pop('doctor')
            #new working logic
            elif user and user.role.name not in ['ADMINISTRATOR', 'DOCTOR', 'PATIENT', 'NURSE']:
                # Instead of hiding the doctor field, disable it for non-admin, non-doctor, non-patient, non-nurse users
                self.fields['doctor'].disabled = True
            
            # Hide priority field for patients (will be set in backend)
            if user and user.role.name == 'PATIENT':
                self.fields['priority'].widget = forms.HiddenInput()
            
            # Set required fields
            required_fields = ['patient', 'scheduled_datetime', 'chief_complaint', 'doctor']
            for field in required_fields:
                if field in self.fields:
                    self.fields[field].required = True
            
            # Set default values
            self.fields['consultation_type'].initial = ConsultationType.INITIAL
            self.fields['priority'].initial = ConsultationPriority.MEDIUM
            
            # Add help text
            if 'doctor' in self.fields:
                self.fields['doctor'].help_text = "Select the doctor for this consultation"
            
        except Exception as e:
            logger.error(f"Error initializing consultation form: {str(e)}")
            # Set basic required fields if initialization fails
            for field in ['patient', 'scheduled_datetime', 'chief_complaint', 'doctor']:
                if field in self.fields:
                    self.fields[field].required = True


    def clean(self):
        cleaned_data = super().clean()
        try:
            # Validate duration
            if 'duration_minutes' in cleaned_data:
                duration_value = cleaned_data['duration_minutes']
                try:
                    duration = int(duration_value)
                except (ValueError, TypeError):
                    raise ValidationError("Invalid duration value")
                if duration < 15:
                    raise ValidationError("Consultation duration must be at least 15 minutes")
            
            # Ensure doctor is set
            if 'doctor' not in cleaned_data or not cleaned_data['doctor']:
                raise ValidationError("A doctor must be selected for the consultation")
                
            return cleaned_data
        except Exception as e:
            logger.error(f"Error cleaning consultation form data: {str(e)}")
            raise ValidationError("Error validating form data. Please check your inputs.")
