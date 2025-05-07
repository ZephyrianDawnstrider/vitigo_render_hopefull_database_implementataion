from django.urls import path
from .views import (
    views as v,
    core as c,
    infrastructure as i,
    storage as s,
    communication as com,  
    payment as p,
    integration as itn,
    security as sec,
    monitoring as mon,
    sync,
    backup,
    history,
    export
)

app_name = 'settings'

urlpatterns = [
    path('', v.SettingsManagementView.as_view(), name='settings_dashboard'),
    
    path('core/', c.CoreSettingsView.as_view(), name='core_settings'),

    path('infrastructure/', i.InfrastructureSettingsView.as_view(), name='infrastructure_settings'),

    path('storage/', s.StorageSettingsView.as_view(), name='storage_settings'),

    path('communication/', com.CommunicationSettingsView.as_view(), name='communication_settings'),

    path('payment/', p.PaymentSettingsView.as_view(), name='payment_settings'),

    path('integration/', itn.IntegrationSettingsView.as_view(), name='integration_settings'),

    path('security/', sec.SecuritySettingsView.as_view(), name='security_settings'),

    path('monitoring/', mon.MonitoringSettingsView.as_view(), name='monitoring_settings'),

    path('sync/', sync.sync_settings, name='sync_settings'),

    path('backup/', backup.backup_settings, name='backup_settings'),

    path('history/', history.SettingHistoryView.as_view(), name='settings_history'),

    path('export/', export.export_settings, name='export_settings'),
]