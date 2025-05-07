from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import ReportExport

class ReportGenerationForm(forms.Form):
    PRESET_RANGES = [
        ('7d', 'Last 7 Days'),
        ('14d', 'Last 14 Days'),
        ('1m', 'Last Month'),
        ('3m', 'Last Quarter'),
        ('6m', 'Last 6 Months'),
        ('1y', 'Last Year'),
    ]

    preset_range = forms.ChoiceField(
        choices=PRESET_RANGES,
        initial='7d',
        widget=forms.Select(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        preset_range = cleaned_data.get('preset_range')
        end_date = timezone.now()
        
        if preset_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif preset_range == '14d':
            start_date = end_date - timedelta(days=14)
        elif preset_range == '1m':
            start_date = end_date - timedelta(days=30)
        elif preset_range == '3m':
            start_date = end_date - timedelta(days=90)
        elif preset_range == '6m':
            start_date = end_date - timedelta(days=180)
        else:  # 1y
            start_date = end_date - timedelta(days=365)
        
        cleaned_data['start_date'] = start_date
        cleaned_data['end_date'] = end_date
        return cleaned_data
