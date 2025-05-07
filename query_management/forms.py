from django import forms
from django.contrib.auth import get_user_model
from .models import Query, QueryTag

class QueryCreateForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select user for whom this query is being created"
    )
    
    class Meta:
        model = Query
        fields = [
            'user', 
            'subject', 
            'description',
            'source',
            'priority',
            'status',
            'assigned_to',
            'is_anonymous',
            'contact_email',
            'contact_phone',
            'query_type',
            'expected_response_date',
            'is_patient',
            'tags'
        ]
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'query_type': forms.Select(attrs={'class': 'form-select'}),
            'expected_response_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].help_text = "Brief description of the query"
        self.fields['description'].help_text = "Detailed explanation of the query"
        self.fields['source'].help_text = "Where did this query originate from?"
        self.fields['priority'].help_text = "Set the urgency level of this query"
        self.fields['status'].help_text = "Current state of the query"
        self.fields['assigned_to'].help_text = "Staff member responsible for handling this query"
        self.fields['query_type'].help_text = "Category of the query"
        self.fields['expected_response_date'].help_text = "When should this query be resolved?"
        self.fields['user'].help_text = "Select the user this query is associated with"
        self.fields['is_anonymous'].help_text = "Check if the query should be anonymous"
        self.fields['is_patient'].help_text = "Check if the query is from a patient"
        self.fields['contact_email'].help_text = "Email address for communication"
        self.fields['contact_phone'].help_text = "Phone number for communication"
        self.fields['tags'].help_text = "Add relevant tags for categorization"
        
        # Filter assigned_to to only show staff users
        self.fields['assigned_to'].queryset = get_user_model().objects.filter(is_staff=True)