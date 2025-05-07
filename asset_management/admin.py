from django.contrib import admin
from .models import (
    AssetCategory,
    Asset,
    MaintenanceSchedule,
    AssetDepreciation,
    AssetAudit,
    InsurancePolicy
)

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'depreciation_rate', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['is_active']

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['asset_id', 'name', 'category', 'status', 'condition', 'purchase_date']
    search_fields = ['name', 'asset_id', 'serial_number']
    list_filter = ['status', 'condition', 'category']

@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ['asset', 'maintenance_type', 'scheduled_date', 'status', 'priority']
    search_fields = ['asset__name', 'maintenance_type']
    list_filter = ['status', 'priority']

@admin.register(AssetDepreciation)
class AssetDepreciationAdmin(admin.ModelAdmin):
    list_display = ['asset', 'date', 'current_value', 'depreciation_amount', 'fiscal_year']
    search_fields = ['asset__name', 'fiscal_year']
    list_filter = ['fiscal_year']

@admin.register(AssetAudit)
class AssetAuditAdmin(admin.ModelAdmin):
    list_display = ['asset', 'audit_date', 'status', 'conducted_by']
    search_fields = ['asset__name', 'conducted_by']
    list_filter = ['status']

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['asset', 'policy_number', 'provider', 'start_date', 'end_date', 'status']
    search_fields = ['policy_number', 'asset__name', 'provider']
    list_filter = ['status']
