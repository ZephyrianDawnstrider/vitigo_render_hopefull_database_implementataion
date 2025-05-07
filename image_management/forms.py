from django import forms
from .models import PatientImage, Patient, ImageAnnotation
from datetime import date
from django.conf import settings
from consultation_management.models import Consultation
from django.contrib.auth import get_user_model

class PatientImageUploadForm(forms.ModelForm):
    consultation = forms.ModelChoiceField(
        queryset=Consultation.objects.all(), 
        widget=forms.Select(attrs={
            'class': 'form-select rounded-lg',
        }),
        help_text='Choose the consultation this image belongs to'
    )
    tagged_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.exclude(role__name='PATIENT'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select rounded-lg',
            'size': '5' 
        }),
        help_text='Select one or more staff members to notify about this image'
    )

    class Meta:
        model = PatientImage
        fields = ['patient', 'image_file', 'body_part', 'image_type', 'upload_type', 'consultation', 'date_taken', 'notes', 'is_private', 'tagged_users']
        widgets = {
            'date_taken': forms.DateInput(attrs={'type': 'date', 'max': date.today().isoformat()}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'image_file': 'Upload a clear, well-lit image in JPG or PNG format (max 5MB)',
            'body_part': 'Select the area of the body shown in the image',
            'image_type': 'Indicate whether this image was taken at the clinic or uploaded by the patient',
            'upload_type': 'Specify if this is a progress update or problem report',
            'date_taken': 'Enter the date when this image was captured',
            'notes': 'Add any relevant observations or context about this image',
            'is_private': 'Check this box to restrict access to authorized personnel only',
        }

    def clean_image_file(self):
        image = self.cleaned_data.get('image_file')
        if image:
            if image.size > settings.MAX_UPLOAD_SIZE:
                raise forms.ValidationError(f'Image size cannot exceed {settings.MAX_UPLOAD_SIZE/1024/1024}MB')
            return image
        raise forms.ValidationError('No image file uploaded')

class ImageAnnotationForm(forms.ModelForm):
    class Meta:
        model = ImageAnnotation
        fields = ['x_coordinate', 'y_coordinate', 'width', 'height', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'rounded-lg'}),
        }

class AnnotationForm(forms.ModelForm):
    class Meta:
        model = ImageAnnotation
        fields = ['x_coordinate', 'y_coordinate', 'width', 'height', 'text']
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'class': 'rounded-lg w-full',
                'placeholder': 'Enter annotation details...'
            })
        }
