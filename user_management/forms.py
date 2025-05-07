from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from access_control.models import Role

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'PATIENT'
        if commit:
            user.save()
        return user

class UserLoginForm(forms.Form):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'pl-10 w-full py-2 border border-[#cbd5e0] rounded-md focus:outline-none focus:border-[#1a365d]',
            'placeholder': 'Enter your email'
        })
    )
    country_code = forms.CharField(
        required=False,
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'pl-3 w-20 py-2 border border-[#cbd5e0] rounded-l-md focus:outline-none focus:border-[#1a365d]',
            'placeholder': '+91'
        })
    )
    phone = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'pl-3 w-full py-2 border border-[#cbd5e0] rounded-r-md focus:outline-none focus:border-[#1a365d]',
            'placeholder': 'Enter your phone number'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'pl-10 w-full py-2 border border-[#cbd5e0] rounded-md focus:outline-none focus:border-[#1a365d]',
            'placeholder': 'Enter your password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        country_code = cleaned_data.get('country_code')
        phone = cleaned_data.get('phone')

        if not email and not phone:
            raise forms.ValidationError("Please provide either email or phone number")
        
        if phone and not country_code:
            raise forms.ValidationError("Country code is required with phone number")

        return cleaned_data


class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'accept': 'image/*'
        })
    )
    country_code = forms.CharField(
        max_length=5,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'placeholder': '+91'
        })
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password', 
                 'role', 'gender', 'country_code', 'phone_number', 'profile_picture', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 pl-10 border border-gray-300 rounded-md'
                })
        
        # Add help text for each field
        self.fields['email'].help_text = "Enter a valid email address. This will be used for login."
        self.fields['first_name'].help_text = "Enter your first name as it appears on official documents."
        self.fields['last_name'].help_text = "Enter your last name as it appears on official documents."
        self.fields['password'].help_text = "Create a strong password with at least 8 characters including letters, numbers and symbols."
        self.fields['confirm_password'].help_text = "Enter the same password as above for verification."
        self.fields['role'].help_text = "Select the appropriate role for this user (e.g., Patient, Doctor, Staff)."
        self.fields['gender'].help_text = "Select your gender identity."
        self.fields['country_code'].help_text = "Enter your country code (e.g., +91 for India)."
        self.fields['phone_number'].help_text = "Enter your phone number without country code."
        self.fields['profile_picture'].help_text = "Upload a clear photo of yourself (optional). Max size: 5MB."
        self.fields['is_active'].help_text = "Check this box to make the account active immediately."

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'gender', 
                 'country_code', 'phone_number', 'role', 'is_active',
                 'profile_picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput)):
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
                })
        
        self.fields['role'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'
        })
        
        self.fields['profile_picture'].widget.attrs.update({
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md',
            'accept': 'image/*'
        })
        
        # Add help text for each field
        self.fields['email'].help_text = "Update the email address. This will be used for login."
        self.fields['first_name'].help_text = "User's first name as it appears on official documents."
        self.fields['last_name'].help_text = "User's last name as it appears on official documents."
        self.fields['gender'].help_text = "Select the user's gender identity."
        self.fields['country_code'].help_text = "Country code for phone number (e.g., +91 for India)."
        self.fields['phone_number'].help_text = "Contact number without country code."
        self.fields['role'].help_text = "User's system role determines their permissions and access levels."
        self.fields['is_active'].help_text = "Inactive accounts cannot log in to the system."
        self.fields['profile_picture'].help_text = "Profile photo should be clear and professional. Max size: 5MB."