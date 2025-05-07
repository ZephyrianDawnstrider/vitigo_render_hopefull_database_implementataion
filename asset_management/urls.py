from django.urls import path
from .views import (
    assets,
    dashboard,
    maintenance,
    audits,
    insurances,
    export,
)

urlpatterns = [
    path('dashboard/', dashboard.AssetDashboardView.as_view(), name='asset_dashboard'),
    path('dashboard/export/', export.AssetDashboardExportView.as_view(), name='asset_dashboard_export'),
    
    path('asset/add/', assets.AddAssetView.as_view(), name='add_asset'),
    path('assets/total/', assets.TotalAssetsView.as_view(), name='total_assets'),
    path('asset/<int:asset_id>/', assets.AssetDetailView.as_view(), name='asset_detail'),
    path('asset/<int:asset_id>/edit/', assets.EditAssetView.as_view(), name='edit_asset'),
    path('asset/<int:asset_id>/delete/', assets.AssetDeleteView.as_view(), name='delete_asset'),
    
    path('maintenance/schedule/', maintenance.MaintenanceScheduleView.as_view(), name='maintenance_schedule'),
    path('maintenance/schedule/create/', maintenance.CreateMaintenanceScheduleView.as_view(), name='create_maintenance_schedule'),
    path('maintenance/<int:schedule_id>/edit/', maintenance.EditMaintenanceScheduleView.as_view(), name='edit_maintenance'),
    path('maintenance/<int:schedule_id>/delete/', maintenance.DeleteMaintenanceScheduleView.as_view(), name='delete_maintenance'),
    
    path('audits/total/', audits.TotalAuditsView.as_view(), name='total_audits'),
    path('audits/create/', audits.CreateAssetAuditView.as_view(), name='create_audit'),
    path('audits/<int:audit_id>/', audits.AssetAuditDetailView.as_view(), name='audit_detail'),
    path('audits/<int:audit_id>/update/', audits.UpdateAssetAuditView.as_view(), name='update_audit'),
    path('audits/<int:audit_id>/complete/', audits.CompleteAssetAuditView.as_view(), name='complete_audit'),
    path('audits/<int:audit_id>/cancel/', audits.CancelAssetAuditView.as_view(), name='cancel_audit'),
    
    path('insurances/total/', insurances.TotalInsurancesView.as_view(), name='total_insurances'),
    path('insurances/create/', insurances.CreateInsurancePolicyView.as_view(), name='create_insurance'),
    path('insurances/<int:policy_id>/', insurances.InsurancePolicyDetailView.as_view(), name='insurance_detail'),
    path('insurances/<int:policy_id>/renew/', insurances.RenewInsurancePolicyView.as_view(), name='renew_insurance'),
    path('insurances/<int:policy_id>/cancel/', insurances.CancelInsurancePolicyView.as_view(), name='cancel_insurance'),
]