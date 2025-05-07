from django import forms
from .models import Medication, MedicationStock, StockAdjustment

class MedicationForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'}),
        help_text="Enter the initial quantity of medication to be added to inventory"
    )
    reorder_level = forms.IntegerField(
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'}),
        help_text="Minimum stock level at which reorder notification will be triggered"
    )

    class Meta:
        model = Medication
        fields = ['name', 'generic_name', 'description', 'dosage_form', 'strength',
                 'manufacturer', 'price', 'requires_prescription']
        help_texts = {
            'name': 'Brand or commercial name of the medication',
            'generic_name': 'Scientific or generic name of the medication',
            'description': 'Brief description of the medication and its uses',
            'dosage_form': 'Form of medication (e.g., tablet, capsule, syrup, injection)',
            'strength': 'Medication strength (e.g., 500mg, 10ml)',
            'manufacturer': 'Company that manufactures this medication',
            'price': 'Retail price per unit in ₹',
            'requires_prescription': 'Check if this medication requires a prescription for dispensing',
        }

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['medication', 'adjustment_type', 'quantity', 'reason', 'reference_number']
        widgets = {
            'medication': forms.Select(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }),
            'adjustment_type': forms.Select(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }),
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5'
            })
        }
        help_texts = {
            'medication': 'Select the medication to adjust stock for',
            'adjustment_type': 'Select whether you are adding or removing stock',
            'quantity': 'Enter the quantity to adjust (positive for additions, negative for removals)',
            'reason': 'Provide a detailed reason for this stock adjustment',
            'reference_number': 'Optional: Enter any reference number (e.g., delivery note, damage report)'
        }