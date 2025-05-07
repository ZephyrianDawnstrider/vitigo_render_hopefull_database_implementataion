from django import forms
from .models import Asset, MaintenanceSchedule, InsurancePolicy, AssetAudit
from datetime import date

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'name', 'asset_id', 'category', 'description', 
            'model_number', 'serial_number', 'manufacturer',
            'purchase_date', 'purchase_cost', 'warranty_expiry',
            'vendor', 'vendor_contact', 'status', 'condition',
            'location', 'specifications', 'power_rating',
            'dimensions', 'weight', 'user_manual', 'certificate',
            'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter asset name',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'asset_id': forms.TextInput(attrs={
                'placeholder': 'Enter unique asset ID',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Detailed description of the asset'
            }),
            'model_number': forms.TextInput(attrs={
                'placeholder': 'Enter model number'
            }),
            'serial_number': forms.TextInput(attrs={
                'placeholder': 'Enter serial number'
            }),
            'manufacturer': forms.TextInput(attrs={
                'placeholder': 'Enter manufacturer name'
            }),
            'purchase_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'purchase_cost': forms.NumberInput(attrs={
                'placeholder': 'Enter purchase cost',
                'step': '0.01'
            }),
            'warranty_expiry': forms.DateInput(attrs={
                'type': 'date'
            }),
            'vendor': forms.TextInput(attrs={
                'placeholder': 'Enter vendor name'
            }),
            'vendor_contact': forms.TextInput(attrs={
                'placeholder': 'Enter vendor contact details'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Enter asset location'
            }),
            'specifications': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Enter technical specifications'
            }),
            'power_rating': forms.TextInput(attrs={
                'placeholder': 'e.g., 240V/50Hz, 1000W'
            }),
            'dimensions': forms.TextInput(attrs={
                'placeholder': 'e.g., 100cm x 50cm x 75cm'
            }),
            'weight': forms.TextInput(attrs={
                'placeholder': 'e.g., 25kg'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Additional notes or remarks'
            }),
        }
        help_texts = {
            'name': 'A clear, descriptive name for the asset',
            'asset_id': 'Unique identifier for the asset (alphanumeric)',
            'category': 'The type or category this asset belongs to',
            'description': 'Detailed description including key features and purpose',
            'model_number': 'Manufacturer\'s model number or product code',
            'serial_number': 'Unique serial number from manufacturer',
            'manufacturer': 'Name of the asset manufacturer',
            'purchase_date': 'Date when the asset was purchased',
            'purchase_cost': 'Original purchase cost in your currency',
            'warranty_expiry': 'Date when the warranty expires',
            'vendor': 'Name of the supplier or vendor',
            'vendor_contact': 'Contact information for the vendor',
            'status': 'Current operational status of the asset',
            'condition': 'Physical condition of the asset',
            'location': 'Current physical location of the asset',
            'specifications': 'Technical specifications in JSON format',
            'power_rating': 'Power consumption or rating details',
            'dimensions': 'Physical dimensions of the asset',
            'weight': 'Weight of the asset',
            'user_manual': 'Upload user manual (PDF only)',
            'certificate': 'Upload relevant certificates (PDF only)',
            'notes': 'Any additional notes or special instructions'
        }
        labels = {
            'asset_id': 'Asset ID',
            'specifications': 'Technical Specifications',
            'power_rating': 'Power Rating',
            'user_manual': 'User Manual (PDF)',
            'certificate': 'Certificates (PDF)',
        }

    def clean(self):
        cleaned_data = super().clean()
        warranty_expiry = cleaned_data.get('warranty_expiry')
        purchase_date = cleaned_data.get('purchase_date')

        if warranty_expiry and purchase_date and warranty_expiry < purchase_date:
            raise forms.ValidationError("Warranty expiry date cannot be earlier than purchase date")
        
        return cleaned_data

class MaintenanceScheduleForm(forms.ModelForm):
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'asset', 'maintenance_type', 'description', 'scheduled_date',
            'priority', 'estimated_duration_hours', 'cost_estimate', 'vendor'
        ]
        widgets = {
            'asset': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'maintenance_type': forms.TextInput(attrs={
                'placeholder': 'e.g., Preventive, Corrective, Inspection',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Detailed description of maintenance work',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'priority': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'estimated_duration_hours': forms.NumberInput(attrs={
                'step': '0.5',
                'placeholder': 'Enter estimated hours',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'cost_estimate': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Enter estimated cost',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'vendor': forms.TextInput(attrs={
                'placeholder': 'Enter vendor/service provider name',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            })
        }
        help_texts = {
            'asset': 'Select the asset that requires maintenance',
            'maintenance_type': 'Type of maintenance to be performed (e.g., Preventive, Corrective, Inspection)',
            'description': 'Provide a detailed description of the maintenance work to be performed',
            'scheduled_date': 'Date when the maintenance is planned to be performed',
            'priority': 'Priority level of the maintenance task (High/Medium/Low)',
            'estimated_duration_hours': 'Estimated time required to complete the maintenance (in hours)',
            'cost_estimate': 'Estimated cost for the maintenance work',
            'vendor': 'Name of the vendor or service provider who will perform the maintenance'
        }
        labels = {
            'asset': 'Asset',
            'maintenance_type': 'Maintenance Type',
            'description': 'Maintenance Description',
            'scheduled_date': 'Scheduled Date',
            'priority': 'Priority Level',
            'estimated_duration_hours': 'Estimated Duration (hours)',
            'cost_estimate': 'Estimated Cost',
            'vendor': 'Vendor/Service Provider'
        }

    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        
        if scheduled_date and scheduled_date < date.today():
            raise forms.ValidationError("Scheduled date cannot be in the past")
        
        return cleaned_data

class InsurancePolicyForm(forms.ModelForm):
    class Meta:
        model = InsurancePolicy
        fields = [
            'asset', 'policy_number', 'provider', 'coverage_type',
            'coverage_amount', 'premium_amount', 'start_date', 'end_date',
            'deductible', 'documents', 'notes'
        ]
        widgets = {
            'asset': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'policy_number': forms.TextInput(attrs={
                'placeholder': 'Enter policy number',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'provider': forms.TextInput(attrs={
                'placeholder': 'Enter insurance provider name',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'coverage_type': forms.TextInput(attrs={
                'placeholder': 'e.g., Comprehensive, Third Party',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'coverage_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Enter coverage amount',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'premium_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Enter premium amount',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'deductible': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Enter deductible amount',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Additional notes or remarks',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            })
        }
        help_texts = {
            'asset': 'Select the asset to be insured',
            'policy_number': 'Unique policy number from insurance provider',
            'provider': 'Name of the insurance provider',
            'coverage_type': 'Type of insurance coverage',
            'coverage_amount': 'Total amount covered by the policy',
            'premium_amount': 'Premium amount to be paid',
            'start_date': 'Policy start date',
            'end_date': 'Policy end date',
            'deductible': 'Deductible amount for claims',
            'notes': 'Any additional notes about the policy'
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data

class AssetAuditForm(forms.ModelForm):
    class Meta:
        model = AssetAudit
        fields = [
            'asset', 'audit_date', 'location_verified', 'condition_verified',
            'discrepancies', 'status', 'conducted_by', 'verified_by',
            'notes', 'photos'
        ]
        widgets = {
            'asset': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'audit_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'location_verified': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'condition_verified': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'discrepancies': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'List any discrepancies found during audit',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'conducted_by': forms.TextInput(attrs={
                'placeholder': 'Name of person conducting the audit',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'verified_by': forms.TextInput(attrs={
                'placeholder': 'Name of person verifying the audit',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Additional notes or observations',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm'
            })
        }
        help_texts = {
            'asset': 'Select the asset to be audited',
            'audit_date': 'Date when the audit is conducted',
            'location_verified': 'Confirm if asset location matches records',
            'condition_verified': 'Confirm if asset condition matches records',
            'discrepancies': 'Note any differences from recorded asset information',
            'status': 'Current status of the audit',
            'conducted_by': 'Person conducting the audit',
            'verified_by': 'Person verifying the audit findings',
            'notes': 'Any additional observations or comments',
            'photos': 'Upload photos taken during audit'
        }

    def clean(self):
        cleaned_data = super().clean()
        audit_date = cleaned_data.get('audit_date')
        
        if audit_date and audit_date > date.today():
            raise forms.ValidationError("Audit date cannot be in the future")
        
        return cleaned_data
