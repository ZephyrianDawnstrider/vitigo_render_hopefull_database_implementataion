from django.contrib import admin
from .models import (
    # Core Settings
    SettingCategory,
    SettingDefinition,
    Setting,
    SystemConfiguration,
    SettingHistory,
    # Infrastructure Settings
    LoggingConfiguration,
    CacheConfiguration,
    BackupConfiguration,
    # Storage Settings
    CloudStorageProvider,
    # Communication Settings
    EmailConfiguration,
    SMSProvider,
    NotificationProvider,
    # Payment Settings
    PaymentGateway,
    # Integration Settings
    APIConfiguration,
    SocialMediaCredential,
    # Security Settings
    SecurityConfiguration,
    AuthenticationProvider,
    # Monitoring Settings
    MonitoringConfiguration,
    AnalyticsConfiguration,
)

# Core Settings
@admin.register(SettingCategory)
class SettingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'parent', 'order', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'key')

@admin.register(SettingDefinition)
class SettingDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'category', 'setting_type', 'is_required', 'is_active')
    list_filter = ('category', 'setting_type', 'is_required', 'is_active')
    search_fields = ('name', 'key')

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('definition', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('definition__name',)

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'site_url', 'admin_email', 'default_timezone')

@admin.register(SettingHistory)
class SettingHistoryAdmin(admin.ModelAdmin):
    list_display = ('setting', 'change_type', 'changed_by', 'created_at')
    list_filter = ('change_type', 'changed_by', 'created_at')
    search_fields = ('setting__definition__name', 'changed_by__username')

# Infrastructure Settings
@admin.register(LoggingConfiguration)
class LoggingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'log_level', 'retention_days', 'is_active')
    list_filter = ('log_level', 'is_active')

@admin.register(CacheConfiguration)
class CacheConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'cache_type', 'host', 'port', 'is_active')
    list_filter = ('cache_type', 'is_active')

@admin.register(BackupConfiguration)
class BackupConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'backup_provider', 'is_active')
    list_filter = ('backup_provider', 'is_active')

# Storage Settings
@admin.register(CloudStorageProvider)
class CloudStorageProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'is_active', 'is_default')
    list_filter = ('provider_type', 'is_active', 'is_default')

# Communication Settings
@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'host', 'from_email', 'is_active')
    list_filter = ('provider', 'is_active', 'is_default')

@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'sender_id', 'is_active')
    list_filter = ('provider_type', 'is_active', 'is_default')

@admin.register(NotificationProvider)
class NotificationProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'environment', 'is_active')
    list_filter = ('provider_type', 'environment', 'is_active')

# Payment Settings
@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'gateway_type', 'environment', 'is_active')
    list_filter = ('gateway_type', 'environment', 'is_active')

# Integration Settings
@admin.register(APIConfiguration)
class APIConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_url', 'version', 'auth_type', 'is_active')
    list_filter = ('auth_type', 'is_active')

@admin.register(SocialMediaCredential)
class SocialMediaCredentialAdmin(admin.ModelAdmin):
    list_display = ('platform', 'environment', 'is_active')
    list_filter = ('platform', 'environment', 'is_active')

# Security Settings
@admin.register(SecurityConfiguration)
class SecurityConfigurationAdmin(admin.ModelAdmin):
    list_display = ('jwt_expiry_hours', 'enable_rate_limiting', 'enable_audit_trail')
    list_filter = ('enable_rate_limiting', 'enable_audit_trail')

@admin.register(AuthenticationProvider)
class AuthenticationProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'is_active', 'is_default')
    list_filter = ('provider_type', 'is_active', 'is_default')

# Monitoring Settings
@admin.register(MonitoringConfiguration)
class MonitoringConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'is_active')
    list_filter = ('provider', 'is_active')

@admin.register(AnalyticsConfiguration)
class AnalyticsConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'tracking_id', 'is_active')
    list_filter = ('provider', 'is_active')
