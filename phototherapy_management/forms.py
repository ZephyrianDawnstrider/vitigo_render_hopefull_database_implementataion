# Standard Library imports
import logging
from datetime import datetime

# Django Core imports
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe

# Local/Relative imports
from .models import (
    DeviceMaintenance,
    PatientRFIDCard,
    PhototherapyDevice,
    PhototherapyPackage,
    PhototherapyPayment,
    PhototherapyPlan,
    PhototherapyProtocol,
    PhototherapyReminder,
    PhototherapySession,
    PhototherapyType,
    ProblemReport,
    PhototherapyCenter
)

# Configure logging
logger = logging.getLogger(__name__)

# Get User model
User = get_user_model()

class ProtocolForm(forms.ModelForm):
    increment_percentage = forms.FloatField(
        initial=10.0,  # Set a default value
        min_value=0,
        max_value=100,
        help_text='Percentage to increase dose each session (0-100). Default is 10%'
    )

    class Meta:
        model = PhototherapyProtocol
        fields = [
            'name',
            'phototherapy_type',
            'description',
            'initial_dose',
            'max_dose',
            'increment_percentage',
            'frequency_per_week',
            'duration_weeks',
            'contraindications',
            'safety_guidelines',
            'is_active'
        ]
        help_texts = {
            'name': 'A unique, descriptive name for the protocol',
            'phototherapy_type': 'Select the type of phototherapy this protocol is for',
            'description': 'Detailed description of the protocol and its intended use',
            'initial_dose': 'Starting dose in mJ/cm². Must be less than maximum dose',
            'max_dose': 'Maximum allowable dose in mJ/cm²',
            'increment_percentage': 'Percentage to increase dose each session (0-100)',
            'frequency_per_week': 'Number of sessions recommended per week',
            'duration_weeks': 'Total duration of the protocol in weeks',
            'contraindications': 'List any conditions where this protocol should not be used',
            'safety_guidelines': 'Important safety information and guidelines for this protocol',
            'is_active': 'Uncheck to disable this protocol'
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'contraindications': forms.Textarea(attrs={'rows': 3}),
            'safety_guidelines': forms.Textarea(attrs={'rows': 3}),
            'initial_dose': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'max_dose': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
            'increment_percentage': forms.NumberInput(attrs={'min': '0', 'max': '100'}),
            'frequency_per_week': forms.NumberInput(attrs={'min': '1', 'max': '7'}),
            'duration_weeks': forms.NumberInput(attrs={'min': '1'})
        }

    def clean(self):
        cleaned_data = super().clean()
        try:
            initial_dose = cleaned_data.get('initial_dose')
            max_dose = cleaned_data.get('max_dose')
            increment_percentage = cleaned_data.get('increment_percentage')

            # Log the validation process
            logger.info(f"Validating protocol form - Initial dose: {initial_dose}, "
                       f"Max dose: {max_dose}, Increment: {increment_percentage}")

            if initial_dose and max_dose:
                if initial_dose > max_dose:
                    raise ValidationError({
                        'initial_dose': 'Initial dose cannot exceed maximum dose',
                        'max_dose': 'Maximum dose must be greater than initial dose'
                    })

            # Validate increment percentage
            if increment_percentage is None:
                increment_percentage = 10.0  # Default value if not provided
                cleaned_data['increment_percentage'] = increment_percentage
            elif increment_percentage < 0 or increment_percentage > 100:
                raise ValidationError({
                    'increment_percentage': 'Increment percentage must be between 0 and 100'
                })

            # Additional validations
            if initial_dose is not None and initial_dose <= 0:
                self.add_error('initial_dose', 'Initial dose must be greater than 0')
            
            if max_dose is not None and max_dose <= 0:
                self.add_error('max_dose', 'Maximum dose must be greater than 0')

            return cleaned_data
        except Exception as e:
            logger.error(f"Error in protocol form validation: {str(e)}")
            raise ValidationError("An error occurred during form validation")
    

class PhototherapyDeviceForm(forms.ModelForm):
    class Meta:
        model = PhototherapyDevice
        fields = [
            'name', 
            'model_number', 
            'serial_number',
            'phototherapy_type',
            'location',
            'installation_date',
            'last_maintenance_date',
            'next_maintenance_date',
            'maintenance_notes'
        ]
        widgets = {
            'installation_date': forms.DateInput(attrs={'type': 'date'}),
            'last_maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'next_maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'maintenance_notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'name': 'Name of the phototherapy device or unit',
            'model_number': 'Manufacturer model number of the device',
            'serial_number': 'Unique serial number of the device',
            'phototherapy_type': 'Type of phototherapy this device delivers',
            'location': 'Physical location of the device in the facility',
            'installation_date': 'Date when the device was installed',
            'last_maintenance_date': 'Date of the most recent maintenance',
            'next_maintenance_date': 'Scheduled date for next maintenance',
            'maintenance_notes': 'Any additional notes about device maintenance'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active phototherapy types
        self.fields['phototherapy_type'].queryset = PhototherapyType.objects.filter(is_active=True)
        
        # Add classes and placeholders
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            if field_name != 'maintenance_notes':  # Don't add required to optional field
                field.widget.attrs['required'] = 'required'


class ScheduleMaintenanceForm(forms.ModelForm):
    class Meta:
        model = DeviceMaintenance
        fields = [
            'device',
            'maintenance_type',
            'maintenance_date',
            'performed_by',
            'description',
            'cost',
            'next_maintenance_due',
            'parts_replaced',
            'notes'
        ]
        widgets = {
            'maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'next_maintenance_due': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'parts_replaced': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active devices
        self.fields['device'].queryset = PhototherapyDevice.objects.filter(is_active=True)
        
        # Add classes and customize labels
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            if field_name in ['device', 'maintenance_type', 'maintenance_date', 'performed_by']:
                field.widget.attrs['required'] = 'required'


class TreatmentPlanForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role__name='PATIENT', is_active=True),
        empty_label="Select Patient",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select the patient who will receive the phototherapy treatment"
    )
    
    protocol = forms.ModelChoiceField(
        queryset=PhototherapyProtocol.objects.filter(is_active=True),
        empty_label="Select Protocol",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Choose the treatment protocol to follow. This determines the treatment parameters"
    )
    
    rfid_card = forms.ModelChoiceField(
        queryset=PatientRFIDCard.objects.filter(is_active=True),
        required=False,
        empty_label="Select RFID Card (Optional)",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Assign an RFID card for access control (required for Wholebody NB and Excimer treatments)"
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="When should the treatment plan begin? Select today or a future date"
    )

    total_sessions_planned = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Total number of sessions planned for this treatment course"
    )

    current_dose = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        help_text="Initial dose in mJ/cm². Must not exceed protocol maximum dose"
    )

    total_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        help_text="Total cost of the treatment plan in INR"
    )

    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        help_text="Any special instructions or precautions for this patient's treatment"
    )

    reminder_frequency = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="How often to send reminders (in days). Recommended: 1-3 days"
    )

    # Add payment fields
    payment_type = forms.ChoiceField(
        choices=PhototherapyPayment.PAYMENT_TYPE,
        widget=forms.RadioSelect(attrs={'class': 'payment-type-radio'}),
        help_text="Select how the patient wishes to pay for the treatment"
    )

    payment_method = forms.ChoiceField(
        choices=PhototherapyPayment.PAYMENT_METHOD,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select the payment method"
    )

    number_of_installments = forms.IntegerField(
        required=False,
        min_value=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Number of installments (if paying in installments)"
    )

    immediate_payment = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        help_text="Collect first payment now"
    )

    center = forms.ModelChoiceField(
        queryset=PhototherapyCenter.objects.filter(is_active=True),
        empty_label="Select Center",
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select the phototherapy center where the treatment will be administered"
    )

    class Meta:
        model = PhototherapyPlan
        fields = [
            'patient', 'protocol', 'center', 'rfid_card', 'start_date',  # Added center here
            'total_sessions_planned', 'current_dose', 'total_cost',
            'special_instructions', 'reminder_frequency',
            'payment_type', 'payment_method', 'number_of_installments', 'immediate_payment'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholder text for text fields
        self.fields['special_instructions'].widget.attrs['placeholder'] = (
            "Enter any special instructions, precautions, or notes for this treatment plan"
        )
        # Customize patient queryset to include related data
        patient_queryset = User.objects.filter(
            role__name='PATIENT',
            is_active=True
        ).select_related('role')
        
        self.fields['patient'].queryset = patient_queryset
        
        # Enhanced patient label with contact info
        def get_patient_label(user):
            try:
                details = []
                details.append(user.get_full_name())
                if user.email:
                    details.append(f"{user.email}")
                if user.phone_number:
                    details.append(f"{user.phone_number}")
                if user.gender:
                    details.append(f"{user.get_gender_display()}")
                return " | ".join(details)
            except Exception as e:
                logger.error(f"Error generating patient label: {str(e)}")
                return str(user)
        
        self.fields['patient'].label_from_instance = get_patient_label

        # Add center queryset with related data
        center_queryset = PhototherapyCenter.objects.filter(
            is_active=True
        ).prefetch_related('available_devices')
        
        self.fields['center'].queryset = center_queryset
        
        # Enhanced center label with device info
        def get_center_label(center):
            try:
                device_count = center.get_available_device_count()
                return f"{center.name} ({device_count} active devices)"
            except Exception as e:
                logger.error(f"Error generating center label: {str(e)}")
                return str(center)
        
        self.fields['center'].label_from_instance = get_center_label

    def clean(self):
        cleaned_data = super().clean()
        protocol = cleaned_data.get('protocol')
        current_dose = cleaned_data.get('current_dose')
        start_date = cleaned_data.get('start_date')
        payment_type = cleaned_data.get('payment_type')
        number_of_installments = cleaned_data.get('number_of_installments')

        try:
            # Validate dose against protocol limits
            if protocol and current_dose:
                if current_dose > protocol.max_dose:
                    self.add_error('current_dose', 
                        f'Current dose ({current_dose}) cannot exceed protocol maximum dose ({protocol.max_dose})'
                    )
                if current_dose < protocol.initial_dose:
                    self.add_error('current_dose', 
                        f'Current dose ({current_dose}) cannot be less than protocol initial dose ({protocol.initial_dose})'
                    )

            # Validate RFID requirement for specific protocols
            if protocol and protocol.phototherapy_type.requires_rfid:
                rfid_card = cleaned_data.get('rfid_card')
                if not rfid_card:
                    self.add_error('rfid_card', 'RFID card is required for this type of phototherapy')

            # Validate start date
            if start_date:
                from django.utils import timezone
                if start_date < timezone.now().date():
                    self.add_error('start_date', 'Start date cannot be in the past')

            # Validate payment fields
            if payment_type == 'PARTIAL' and not number_of_installments:
                self.add_error('number_of_installments', 'Number of installments is required for partial payments')

        except Exception as e:
            logger.error(f"Error in form validation: {str(e)}")
            self.add_error(None, str(e))
        
        return cleaned_data
    

class ScheduleSessionForm(forms.ModelForm):
    class Meta:
        model = PhototherapySession
        fields = [
            'plan', 
            'scheduled_date', 
            'scheduled_time', 
            'device',
            'planned_dose',
            'administered_by',
            'remarks'  # Add remarks field
        ]
        widgets = {
            'scheduled_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'Select session date'
                }
            ),
            'scheduled_time': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'placeholder': 'Select session time'
                }
            ),
            'remarks': forms.Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200',
                    'placeholder': 'Enter any additional remarks or special instructions for this session'
                }
            )
        }
        help_texts = {
            'plan': 'Select an active treatment plan. Only active plans are shown.',
            'scheduled_date': 'Choose a date within the treatment plan period. Cannot schedule beyond plan end date.',
            'scheduled_time': 'Select a time slot. Check device and staff availability.',
            'device': 'Select the phototherapy device to be used. Only active devices are shown.',
            'planned_dose': 'Enter the planned dose in mJ/cm². Must be within protocol limits.',
            'remarks': 'Add any additional remarks, special instructions, or notes for this session.'
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Filter active plans only
            self.fields['plan'].queryset = PhototherapyPlan.objects.filter(is_active=True)
            
            # Filter active devices and exclude those needing maintenance
            from django.utils import timezone
            self.fields['device'].queryset = PhototherapyDevice.objects.filter(
                is_active=True
            ).exclude(
                next_maintenance_date__lte=timezone.now().date()
            )
            
            # Add Bootstrap classes and enhance help texts
            for field in self.fields:
                self.fields[field].widget.attrs.update({
                    'class': 'form-control rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200'
                })
            
            # Update device field help text to explain filtering
            self.fields['device'].help_text = (
                'Select the phototherapy device to be used. Only active devices that are not due for maintenance are shown. ' 
                'Some devices may not be available if they require maintenance.'
            )

            # Add detailed help text for each field
            self.fields['plan'].help_text += ' The selected plan determines available devices and dose ranges.'
            self.fields['scheduled_date'].help_text += ' Sessions must be scheduled at least 24 hours in advance.'
            self.fields['scheduled_time'].help_text += ' Consider patient preference and clinic hours.'
            self.fields['device'].help_text += ' Ensure device maintenance status and availability.'
            self.fields['planned_dose'].help_text += f' Recommended range: {self.get_dose_range()}'

            # Customize administered_by field with expanded role filtering and error handling
            excluded_roles = ['PATIENT', 'HR_STAFF', 'INVENTORY_MANAGER', 'BILLING_STAFF', 'LAB_TECHNICIAN', 'PHARMACIST', 'RECEPTIONIST', 'MANAGER']
            staff_queryset = User.objects.filter(
                is_active=True
            ).exclude(
                role__name__in=excluded_roles
            ).select_related('role')  # Optimize by preloading role

            # Verify queryset has results
            if not staff_queryset.exists():
                logger.warning("No eligible staff members found for administered_by field")
                staff_queryset = User.objects.none()

            self.fields['administered_by'] = forms.ModelChoiceField(
                queryset=staff_queryset,
                empty_label="Select staff member",
                help_text="Select the medical staff member who will administer the session",
                required=True  # Make this field required
            )

            # Custom label_from_instance for administered_by with error handling
            def get_staff_label(user):
                try:
                    if user and user.role:
                        return f"{user.get_full_name()} ({user.role.name})"
                    return f"{user.get_full_name()} (Role not assigned)" if user else "Unknown Staff"
                except Exception as e:
                    logger.error(f"Error generating staff label: {str(e)}")
                    return "Staff Member"

            self.fields['administered_by'].label_from_instance = get_staff_label

            # Configure plan field with enhanced filtering and error handling
            active_plans = (PhototherapyPlan.objects.filter(is_active=True)
                          .select_related(
                              'patient__patient_profile__user',
                              'protocol'
                          ).order_by('patient__first_name'))

            # Verify queryset has results
            if not active_plans.exists():
                logger.warning("No active treatment plans found")
                active_plans = PhototherapyPlan.objects.none()

            self.fields['plan'] = forms.ModelChoiceField(
                queryset=active_plans,
                empty_label="Select treatment plan",
                help_text="Select an active treatment plan. Search by patient name or protocol.",
                required=True
            )

            # Custom label_from_instance for plan to show detailed info with correct session count
            def get_plan_label(plan):
                try:
                    if plan and plan.patient and plan.protocol:
                        # Update sessions completed count first
                        completed_count = plan.sessions.filter(status='COMPLETED').count()
                        if completed_count != plan.sessions_completed:
                            plan.sessions_completed = completed_count
                            plan.save(update_fields=['sessions_completed'])
                            
                        return (f"{plan.patient.get_full_name()} - {plan.protocol.name} "
                               f"(Sessions: {completed_count}/{plan.total_sessions_planned})")
                    return "Unknown Plan"
                except Exception as e:
                    logger.error(f"Error generating plan label: {str(e)}")
                    return "Treatment Plan"

            self.fields['plan'].label_from_instance = get_plan_label
            
            # Configure device field with enhanced filtering and error handling
            active_devices = (PhototherapyDevice.objects.filter(
                is_active=True
            ).exclude(
                next_maintenance_date__lte=timezone.now().date()
            ).select_related('phototherapy_type'))

            # Verify queryset has results
            if not active_devices.exists():
                logger.warning("No active devices found")
                active_devices = PhototherapyDevice.objects.none()

            self.fields['device'] = forms.ModelChoiceField(
                queryset=active_devices,
                empty_label="Select device",
                help_text="Select an available device. Search by name or location.",
                required=True
            )

            # Custom label_from_instance for device to show detailed info
            def get_device_label(device):
                try:
                    if device:
                        maintenance_status = "Maintenance Required" if device.needs_maintenance() else "Available"
                        return f"{device.name} - {device.location} ({maintenance_status})"
                    return "Unknown Device"
                except Exception as e:
                    logger.error(f"Error generating device label: {str(e)}")
                    return "Device"

            self.fields['device'].label_from_instance = get_device_label

        except Exception as e:
            logger.error(f"Error initializing ScheduleSessionForm: {str(e)}")
            self.fields['plan'].queryset = PhototherapyPlan.objects.none()
            self.fields['plan'].help_text = "Error loading treatment plans. Please contact administrator."

    def get_dose_range(self):
        """Get recommended dose range based on protocol defaults"""
        try:
            return "100-2000 mJ/cm² (varies by protocol)"
        except Exception as e:
            logger.error(f"Error getting dose range: {str(e)}")
            return "Contact administrator for recommended range"

    def clean(self):
        cleaned_data = super().clean()
        try:
            plan = cleaned_data.get('plan')
            scheduled_date = cleaned_data.get('scheduled_date')
            scheduled_time = cleaned_data.get('scheduled_time')
            planned_dose = cleaned_data.get('planned_dose')

            if not all([plan, scheduled_date, scheduled_time, planned_dose]):
                # Skip validation if required fields are missing
                return cleaned_data

            # Check if the plan is still active on the scheduled date
            if plan.end_date and scheduled_date > plan.end_date:
                self.add_error('scheduled_date', 
                    f"Cannot schedule session after plan end date ({plan.end_date})")

            # Check if there's already a session scheduled for this time
            if PhototherapySession.objects.filter(
                plan=plan,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time
            ).exists():
                self.add_error('scheduled_time', 
                    "A session is already scheduled for this time slot")

            # Validate dose against plan protocol
            protocol = plan.protocol
            if planned_dose > protocol.max_dose:
                self.add_error('planned_dose', 
                    f"Dose ({planned_dose} mJ/cm²) exceeds maximum allowed ({protocol.max_dose} mJ/cm²)")
            if planned_dose < protocol.initial_dose:
                self.add_error('planned_dose', 
                    f"Dose ({planned_dose} mJ/cm²) below minimum recommended ({protocol.initial_dose} mJ/cm²)")

            # Check if scheduled date is in the past
            from django.utils import timezone
            if scheduled_date < timezone.now().date():
                self.add_error('scheduled_date', "Cannot schedule sessions in the past")

            # Validate device availability if selected
            device = cleaned_data.get('device')
            if device and not device.is_active:
                self.add_error('device', "Selected device is currently inactive")
            if device and device.needs_maintenance():
                self.add_error('device', "Selected device requires maintenance")

        except Exception as e:
            logger.error(f"Error in form validation: {str(e)}")
            self.add_error(None, f"An error occurred during validation: {str(e)}")

        return cleaned_data

    def clean_administered_by(self):
        administered_by = self.cleaned_data.get('administered_by')
        if not administered_by:
            raise forms.ValidationError("Please select a staff member to administer the session")
            
        try:
            # Verify the selected user is still valid
            if not administered_by.is_active:
                raise forms.ValidationError("Selected staff member is no longer active")
                
            # Verify the user has a valid role
            if not hasattr(administered_by, 'role') or not administered_by.role:
                raise forms.ValidationError("Selected staff member has no assigned role")
                
            # Verify the role is appropriate
            excluded_roles = ['PATIENT', 'HR_STAFF', 'INVENTORY_MANAGER', 'BILLING_STAFF', 'LAB_TECHNICIAN', 'PHARMACIST', 'RECEPTIONIST', 'MANAGER']
            if administered_by.role.name in excluded_roles:
                raise forms.ValidationError("Selected staff member is not authorized to administer sessions")
                
        except User.DoesNotExist:
            raise forms.ValidationError("Selected staff member not found")
        except Exception as e:
            logger.error(f"Error validating administered_by: {str(e)}")
            raise forms.ValidationError("Error validating staff member selection")
            
        return administered_by

    def clean_plan(self):
        plan = self.cleaned_data.get('plan')
        if not plan:
            raise forms.ValidationError("Please select a treatment plan")
            
        try:
            # Verify the plan is still active
            if not plan.is_active:
                raise forms.ValidationError("Selected treatment plan is no longer active")
                
            # Verify the plan has not exceeded total sessions
            if plan.sessions_completed >= plan.total_sessions_planned:
                raise forms.ValidationError("This treatment plan has completed all planned sessions")
                
            # Verify the plan hasn't expired
            if plan.end_date and plan.end_date < timezone.now().date():
                raise forms.ValidationError("This treatment plan has expired")
                
        except PhototherapyPlan.DoesNotExist:
            raise forms.ValidationError("Selected treatment plan not found")
        except Exception as e:
            logger.error(f"Error validating treatment plan: {str(e)}")
            raise forms.ValidationError("Error validating treatment plan selection")
            
        return plan

    def clean_device(self):
        device = self.cleaned_data.get('device')
        if not device:
            raise forms.ValidationError("Please select a device")
            
        try:
            # Verify the device is still active
            if not device.is_active:
                raise forms.ValidationError("Selected device is currently inactive")
                
            # Verify maintenance status
            if device.needs_maintenance():
                raise forms.ValidationError("Selected device requires maintenance")
                
            # Verify compatible with plan's protocol type
            plan = self.cleaned_data.get('plan')
            if plan and plan.protocol.phototherapy_type != device.phototherapy_type:
                raise forms.ValidationError(
                    "Device type does not match the treatment plan's protocol requirements"
                )
                
        except PhototherapyDevice.DoesNotExist:
            raise forms.ValidationError("Selected device not found")
        except Exception as e:
            logger.error(f"Error validating device: {str(e)}")
            raise forms.ValidationError("Error validating device selection")
            
        return device
    

class PhototherapyTypeForm(forms.ModelForm):
    class Meta:
        model = PhototherapyType
        fields = ['name', 'therapy_type', 'description', 'priority', 'requires_rfid']
        
        help_texts = {
            'name': 'Enter a unique and descriptive name for the therapy type (e.g., "Narrow Band UVB - Full Body")',
            'therapy_type': 'Select the primary category of phototherapy treatment',
            'description': 'Provide detailed information about the therapy type, including its purpose, typical usage, and any special considerations',
            'priority': (
                'Set the priority level for this therapy type: '
                'Blue A (High) for critical/urgent treatments, '
                'Green B (Medium) for standard treatments, '
                'Red C (Low) for optional/supplementary treatments'
            ),
            'requires_rfid': 'Check this if patients need RFID cards to access this therapy type (typically required for self-service equipment)'
        }

        labels = {
            'name': 'Therapy Name',
            'therapy_type': 'Treatment Category',
            'description': 'Detailed Description',
            'priority': 'Priority Level',
            'requires_rfid': 'RFID Access Required'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes and customize widgets for better UX
        for field_name, field in self.fields.items():
            # Common classes for all fields
            css_classes = 'block w-full mt-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            
            # Customize specific fields
            if field_name == 'description':
                field.widget = forms.Textarea(attrs={
                    'class': css_classes,
                    'rows': 4,
                    'placeholder': 'Enter detailed description of the therapy type...'
                })
            elif field_name == 'name':
                field.widget = forms.TextInput(attrs={
                    'class': css_classes,
                    'placeholder': 'Enter therapy type name'
                })
            elif field_name == 'requires_rfid':
                field.widget = forms.CheckboxInput(attrs={
                    'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                })
            else:
                field.widget.attrs.update({'class': css_classes})

        # Add placeholder text for therapy type dropdown
        self.fields['therapy_type'].widget.attrs['placeholder'] = 'Select treatment category'

        # Customize error messages
        self.fields['name'].error_messages = {
            'required': 'Please enter a name for the therapy type',
            'unique': 'This therapy type name already exists'
        }
        
        self.fields['therapy_type'].error_messages = {
            'required': 'Please select a treatment category'
        }
        
        self.fields['description'].error_messages = {
            'required': 'Please provide a description of the therapy type'
        }
        
        self.fields['priority'].error_messages = {
            'required': 'Please select a priority level'
        }


class ProblemReportForm(forms.ModelForm):
    session = forms.ModelChoiceField(
        queryset=PhototherapySession.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200'
        }),
        help_text=(
            "Select the phototherapy session for which you want to report a problem. "
            "Shows recent sessions first."
        )
    )
    
    reported_by = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200'
        }),
        help_text=(
            "Select who is reporting this problem. As an administrator, "
            "you can report problems on behalf of others."
        )
    )

    class Meta:
        model = ProblemReport
        fields = ['session', 'reported_by', 'problem_description', 'severity']
        widgets = {
            'problem_description': forms.Textarea(attrs={
                'class': 'form-textarea mt-1 block w-full rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200',
                'rows': 4,
                'placeholder': 'Describe the problem in detail...'
            }),
            'severity': forms.Select(attrs={
                'class': 'form-select rounded-lg border-gray-300 focus:border-blue-500 focus:ring focus:ring-blue-200'
            })
        }
        help_texts = {
            'problem_description': (
                "Provide a detailed description of the problem you encountered. Include:\n\n"
                "• What happened?\n"
                "• When did it occur?\n"
                "• Any symptoms or side effects?\n"
                "• Any relevant circumstances?\n\n"
                "This helps us address the issue more effectively."
            ),
            'severity': (
                "Select the severity level of the problem:\n\n"
                "• NONE: No immediate concerns\n"
                "• MILD: Minor discomfort or issues\n"
                "• MODERATE: Noticeable problems requiring attention\n"
                "• SEVERE: Serious issues requiring immediate action"
            )
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Handle session queryset based on user role
            if user.role.name == 'PATIENT':
                self.fields['session'].queryset = PhototherapySession.objects.filter(
                    plan__patient=user
                )
                # Hide reported_by field for patients and set it to themselves
                self.fields['reported_by'].widget = forms.HiddenInput()
                self.fields['reported_by'].initial = user
                self.fields['reported_by'].queryset = User.objects.filter(id=user.id)
            elif user.role.name in ['ADMIN', 'DOCTOR', 'STAFF']:
                # For admin/staff, show all sessions and all active users
                self.fields['session'].queryset = PhototherapySession.objects.all()
                self.fields['reported_by'].queryset = User.objects.filter(is_active=True)
                self.fields['reported_by'].initial = user
            
            # Add field labels for clarity
            self.fields['session'].label = "Phototherapy Session"
            self.fields['reported_by'].label = "Reported By"
            self.fields['problem_description'].label = "Problem Description"
            self.fields['severity'].label = "Problem Severity"
            
            # Make all fields required
            for field in self.fields:
                self.fields[field].required = True

            # Format the help text with proper line breaks for display
            for field in self.fields:
                if self.fields[field].help_text:
                    self.fields[field].help_text = mark_safe(
                        self.fields[field].help_text.replace('\n', '<br>')
                    )

    def clean(self):
        cleaned_data = super().clean()
        session = cleaned_data.get('session')
        reported_by = cleaned_data.get('reported_by')

        # Additional validation for reported_by field
        if session and reported_by:
            # For patients, ensure they can only report their own sessions
            if reported_by.role.name == 'PATIENT' and session.plan.patient != reported_by:
                raise ValidationError({
                    'session': 'You can only report problems for your own sessions.'
                })

        return cleaned_data
    

class PhototherapyReminderForm(forms.ModelForm):
    scheduled_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-input rounded-lg w-full border-gray-300 focus:border-amber-500 focus:ring-amber-500'
            }
        ),
        help_text="Schedule a future date and time for the reminder. Must be at least 30 minutes from now."
    )

    class Meta:
        model = PhototherapyReminder
        fields = ['plan', 'reminder_type', 'scheduled_datetime', 'message']
        widgets = {
            'plan': forms.Select(attrs={
                'class': 'form-select rounded-lg w-full border-gray-300 focus:border-amber-500 focus:ring-amber-500'
            }),
            'reminder_type': forms.Select(attrs={
                'class': 'form-select rounded-lg w-full border-gray-300 focus:border-amber-500 focus:ring-amber-500'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-textarea rounded-lg w-full border-gray-300 focus:border-amber-500 focus:ring-amber-500',
                'rows': 4,
                'placeholder': (
                    "Dear {patient_name}, your phototherapy session is scheduled for {appointment_time}. "
                    "Please arrive 10 minutes before your appointment time.\n\n"
                    "Message will be automatically formatted with the patient's details."
                )
            }),
        }
        help_texts = {
            'plan': "Select an active treatment plan for the patient.",
            'reminder_type': mark_safe(
                "SESSION: For upcoming phototherapy sessions<br>"
                "PAYMENT: For pending payments<br>"
                "FOLLOWUP: For follow-up appointments<br>"
                "MAINTENANCE: For equipment maintenance"
            ),
            'message': mark_safe(
                "Available variables for message:<br>"
                "{patient_name} - Patient's full name<br>"
                "{appointment_time} - Scheduled time<br>"
                "{treatment_type} - Type of treatment<br>"
                "{clinic_name} - Name of the clinic<br><br>"
                "Message will be sent in the patient's preferred language."
            ),
        }
        labels = {
            'plan': 'Treatment Plan',
            'reminder_type': 'Type of Reminder',
            'scheduled_datetime': 'Schedule For',
            'message': 'Reminder Message'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = self.fields['plan'].queryset.filter(
            is_active=True
        ).select_related('patient').order_by('patient__first_name')
        
        self.fields['plan'].label_from_instance = lambda obj: (
            f"{obj.patient.get_full_name()} - {obj.protocol.name}"
        )

    def clean_scheduled_datetime(self):
        scheduled_datetime = self.cleaned_data.get('scheduled_datetime')
        if scheduled_datetime:
            min_time = timezone.now() + timezone.timedelta(minutes=30)
            if scheduled_datetime < min_time:
                raise forms.ValidationError(
                    "Scheduled time must be at least 30 minutes from now"
                )
        return scheduled_datetime

    def clean_message(self):
        message = self.cleaned_data.get('message')
        reminder_type = self.cleaned_data.get('reminder_type')
        
        if reminder_type in ['SESSION', 'FOLLOWUP', 'PAYMENT'] and '{patient_name}' not in message:
            raise forms.ValidationError("Message must include {patient_name} for patient reminders")
        if reminder_type == 'SESSION' and '{appointment_time}' not in message:
            raise forms.ValidationError("Session reminders must include {appointment_time}")
            
        return message


class PhototherapyPackageForm(forms.ModelForm):
    class Meta:
        model = PhototherapyPackage
        fields = ['name', 'description', 'number_of_sessions', 'total_cost', 
                 'is_featured', 'therapy_type', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter package description...',
                'class': 'form-textarea mt-1 block w-full rounded-lg'
            }),
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter package name',
                'class': 'form-input rounded-lg'
            }),
            'number_of_sessions': forms.NumberInput(attrs={
                'min': '1',
                'class': 'form-input rounded-lg'
            }),
            'total_cost': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01',
                'class': 'form-input rounded-lg'
            })
        }
        help_texts = {
            'name': 'Enter a unique and descriptive name for the package',
            'description': 'Provide detailed information about what the package includes',
            'number_of_sessions': 'Number of phototherapy sessions included in this package',
            'total_cost': 'Total cost of the package in INR',
            'is_featured': 'Featured packages appear at the top of the list',
            'therapy_type': 'Select specific therapy type or leave blank for all types',
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('total_cost', 0) < 0:
            raise ValidationError("Total cost cannot be negative")
        if cleaned_data.get('number_of_sessions', 0) < 1:
            raise ValidationError("Number of sessions must be at least 1")
        return cleaned_data