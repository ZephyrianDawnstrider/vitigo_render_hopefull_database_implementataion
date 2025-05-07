from django import forms
from django.contrib.auth import get_user_model
from .models import Employee, Department, Position, Document, Notice, Training, Grievance, PerformanceReview
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Submit, Button

User = get_user_model()

class EmployeeCreationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        help_text="Legal first name as per documents"
    )
    last_name = forms.CharField(
        max_length=30,
        help_text="Legal last name as per documents"
    )
    email = forms.EmailField(
        help_text="Work email address"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Must be at least 8 characters long with numbers and special characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Re-enter the password to confirm"
    )

    class Meta:
        model = Employee
        fields = [
            'employee_id', 'department', 'position', 'reporting_to',
            'date_of_birth', 'emergency_contact_name', 'emergency_contact_number',
            'address', 'employment_status', 'employment_type', 'join_date',
            'current_salary', 'resume', 'contract_document'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'join_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'employee_id': 'Unique employee identifier',
            'department': 'Select the department where employee will work',
            'position': 'Job title or position',
            'reporting_to': 'Name of the reporting manager',
            'date_of_birth': 'Date of birth as per documents',
            'emergency_contact_name': 'Name of the emergency contact person',
            'emergency_contact_number': 'Phone number of the emergency contact person',
            'address': 'Residential address',
            'employment_status': 'Current employment status',
            'employment_type': 'Full-time, part-time, etc.',
            'join_date': 'Date of joining the company',
            'current_salary': 'Current salary of the employee',
            'resume': 'Accepted formats: PDF, DOC, DOCX (Max 5MB)',
            'contract_document': 'Accepted format: PDF only (Max 5MB)'
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

class EmployeeEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = Employee
        fields = [
            'department', 'position', 'reporting_to',
            'emergency_contact_name', 'emergency_contact_number',
            'address', 'employment_status', 'employment_type',
            'current_salary'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['phone_number'].initial = self.instance.user.phone_number

    def save(self, commit=True):
        employee = super().save(commit=False)
        if commit:
            # Update User model fields
            user = employee.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.phone_number = self.cleaned_data['phone_number']
            user.save()
            employee.save()
        return employee

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'head', 'parent']
        help_texts = {
            'name': 'Full name of the department',
            'code': 'Unique identifier code (3-5 characters)',
            'description': 'Detailed description of the department\'s role and responsibilities',
            'head': 'Employee who will lead this department',
            'parent': 'Parent department if this is a sub-department'
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper()
            # Check if code exists (excluding current instance in case of update)
            exists = Department.objects.filter(code=code)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise forms.ValidationError("This department code already exists")
        return code

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'title', 'description', 'file', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'document_type': 'Select the type of document you are uploading',
            'title': 'Enter a descriptive title for the document',
            'description': 'Provide any additional details about the document',
            'file': 'Upload document in PDF, JPG, JPEG, or PNG format (Max 5MB)',
            'expiry_date': 'Set expiry date if applicable (optional)'
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 5 * 1024 * 1024:  # 5MB
                raise forms.ValidationError("File size must be no more than 5MB")
        return file

class DocumentEditForm(forms.ModelForm):
    keep_file = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Uncheck to replace the current file with a new one"
    )
    
    class Meta:
        model = Document
        fields = ['document_type', 'title', 'description', 'file', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'document_type': 'Type of document',
            'title': 'Document title',
            'description': 'Additional details about the document',
            'file': 'Upload new file (PDF, JPG, JPEG, or PNG format, Max 5MB)',
            'expiry_date': 'Document expiry date (if applicable)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = False

    def clean(self):
        cleaned_data = super().clean()
        keep_file = cleaned_data.get('keep_file')
        new_file = cleaned_data.get('file')
        
        if not keep_file and not new_file:
            raise forms.ValidationError("You must either keep the existing file or upload a new one")
            
        if new_file and new_file.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError("File size must be no more than 5MB")
            
        return cleaned_data

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now().date():
            raise forms.ValidationError("Expiry date cannot be in the past")
        return expiry_date

class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'priority', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'title': 'Enter a clear and concise title for the notice',
            'content': 'Provide the complete notice content',
            'priority': 'Select the importance level of this notice',
            'expiry_date': 'Set an expiry date for the notice (optional)'
        }

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date < timezone.now().date():
            raise forms.ValidationError("Expiry date cannot be in the past")
        return expiry_date

class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = [
            'title', 'description', 'trainer', 'start_date', 
            'end_date', 'location', 'max_participants', 'materials'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'title': 'Enter a clear and descriptive title for the training program',
            'description': 'Provide detailed information about the training content and objectives',
            'trainer': 'Name of the person conducting the training',
            'start_date': 'Training start date',
            'end_date': 'Training end date',
            'location': 'Where the training will be conducted',
            'max_participants': 'Maximum number of participants allowed',
            'materials': 'Upload training materials (PDF, DOC, DOCX, PPT, PPTX only)'
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date cannot be earlier than start date")
            
        return cleaned_data

    def clean_materials(self):
        materials = self.cleaned_data.get('materials')
        if materials:
            if materials.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError("File size must be no more than 10MB")
        return materials

class GrievanceEditForm(forms.ModelForm):
    class Meta:
        model = Grievance
        fields = ['subject', 'description', 'priority', 'status', 'assigned_to', 'resolution', 'is_confidential']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'resolution': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'subject': 'Brief title describing the grievance',
            'description': 'Detailed explanation of the grievance',
            'priority': 'Set the urgency level of the grievance',
            'status': 'Current state of the grievance',
            'assigned_to': 'Staff member responsible for handling this grievance',
            'resolution': 'Details of how the grievance was resolved (required for Resolved/Closed status)',
            'is_confidential': 'Mark if this grievance contains sensitive information'
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        resolution = cleaned_data.get('resolution')

        if status in ['RESOLVED', 'CLOSED'] and not resolution:
            raise forms.ValidationError("Resolution is required when status is Resolved or Closed")

        return cleaned_data

class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = [
            'employee', 'review_date', 'review_period_start', 
            'review_period_end', 'technical_skills', 'communication',
            'teamwork', 'productivity', 'reliability', 'achievements',
            'areas_for_improvement', 'goals', 'overall_comments'
        ]
        widgets = {
            'review_date': forms.DateInput(attrs={'type': 'date'}),
            'review_period_start': forms.DateInput(attrs={'type': 'date'}),
            'review_period_end': forms.DateInput(attrs={'type': 'date'}),
            'achievements': forms.Textarea(attrs={'rows': 3}),
            'areas_for_improvement': forms.Textarea(attrs={'rows': 3}),
            'goals': forms.Textarea(attrs={'rows': 3}),
            'overall_comments': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'employee': 'Select the employee whose performance is being reviewed',
            'review_date': 'Date when this performance review is being conducted',
            'review_period_start': 'Start date of the period being reviewed (e.g., start of quarter/year)',
            'review_period_end': 'End date of the period being reviewed (e.g., end of quarter/year)',
            'technical_skills': 'Rate 1-5: Job knowledge, technical competency, quality of work, and problem-solving abilities',
            'communication': 'Rate 1-5: Verbal/written communication, listening skills, and ability to convey information clearly',
            'teamwork': 'Rate 1-5: Collaboration, cooperation with colleagues, and contribution to team objectives',
            'productivity': 'Rate 1-5: Work efficiency, meeting deadlines, and achieving targets',
            'reliability': 'Rate 1-5: Attendance, punctuality, responsibility, and dependability',
            'achievements': 'List key accomplishments, completed projects, and notable contributions during the review period',
            'areas_for_improvement': 'Identify specific skills, behaviors, or competencies that need development',
            'goals': 'Set SMART goals (Specific, Measurable, Achievable, Relevant, Time-bound) for the next period',
            'overall_comments': 'Provide a comprehensive summary of the employee\'s performance and additional observations'
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('review_period_start')
        end = cleaned_data.get('review_period_end')
        
        if start and end and start > end:
            raise forms.ValidationError("Review period end date must be after start date")
            
        return cleaned_data
