# Standard library imports
from decimal import Decimal

# Django imports
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

# Third-party imports
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField

# Initialize User model
User = get_user_model()

#------------------------------------------------------------------------------
# Core Settings Models
#------------------------------------------------------------------------------

class SettingCategory(models.Model):
    """Categories for organizing different types of settings"""
    name = models.CharField(max_length=100, unique=True)
    key = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Setting Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class SettingDefinition(models.Model):
    """Defines the structure and validation rules for settings"""
    SETTING_TYPES = [
        ('STRING', 'Text String'),
        ('NUMBER', 'Number'),
        ('BOOLEAN', 'Boolean'),
        ('JSON', 'JSON Object'),
        ('EMAIL', 'Email Address'),
        ('URL', 'URL'),
        ('PASSWORD', 'Password'),
        ('FILE', 'File Path'),
        ('COLOR', 'Color Code'),
        ('DATETIME', 'Date and Time'),
        ('LIST', 'List of Values'),
        ('ENCRYPTED', 'Encrypted Value'),
    ]

    category = models.ForeignKey(SettingCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    key = models.SlugField(max_length=100, unique=True)
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES)
    description = models.TextField(blank=True)
    default_value = models.TextField(blank=True, null=True)
    is_required = models.BooleanField(default=False)
    is_sensitive = models.BooleanField(default=False)
    validation_regex = models.CharField(max_length=500, blank=True)
    validation_message = models.CharField(max_length=200, blank=True)
    possible_values = models.JSONField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['category', 'key']


class Setting(models.Model):
    """Stores the actual setting values"""
    definition = models.ForeignKey(
        SettingDefinition,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    value = models.TextField(blank=True, null=True)
    encrypted_value = EncryptedTextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_settings'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_settings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['definition']


class SettingHistory(models.Model):
    """Track changes to settings over time"""
    setting = models.ForeignKey(Setting, on_delete=models.CASCADE, related_name='history')
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey('user_management.CustomUser', on_delete=models.SET_NULL, null=True)
    change_type = models.CharField(
        max_length=20,
        choices=[
            ('CREATE', 'Created'),
            ('UPDATE', 'Updated'),
            ('DELETE', 'Deleted'),
            ('SYNC', 'Synchronized'),
            ('BACKUP', 'Backed Up'),
        ]
    )
    change_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Setting Histories'


class SystemConfiguration(models.Model):
    """Global system configuration settings"""
    site_name = models.CharField(max_length=100)
    site_url = models.URLField()
    admin_email = models.EmailField()
    session_timeout_minutes = models.PositiveIntegerField(default=30)
    password_expiry_days = models.PositiveIntegerField(default=90)
    max_login_attempts = models.PositiveIntegerField(default=5)
    require_2fa = models.BooleanField(default=False)
    max_upload_size_mb = models.PositiveIntegerField(default=5)
    allowed_file_extensions = models.JSONField(
        default=list,
        help_text="Allowed file extensions for uploads",
        null=True,
        blank=True
    )
    default_timezone = models.CharField(max_length=50, default='UTC')
    default_language = models.CharField(max_length=10, default='en-us')
    date_format = models.CharField(max_length=50, default='YYYY-MM-DD')
    time_format = models.CharField(max_length=50, default='HH:mm:ss')
    business_hours = models.JSONField(
        default=dict,
        help_text="Business hours configuration",
        null=True,
        blank=True
    )
    holiday_calendar = models.JSONField(
        default=list,
        help_text="Holiday calendar configuration",
        null=True,
        blank=True
    )
    appointment_duration_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"

#------------------------------------------------------------------------------
# Infrastructure Settings Models
#------------------------------------------------------------------------------

class LoggingConfiguration(models.Model):
    """Configuration for system logging"""
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    name = models.CharField(max_length=100)
    log_level = models.CharField(max_length=10, choices=LOG_LEVELS, default='INFO')
    log_file_path = models.CharField(max_length=255)
    rotation_policy = models.JSONField()
    retention_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)


class CacheConfiguration(models.Model):
    """Configuration for caching system"""
    CACHE_TYPES = [
        ('REDIS', 'Redis'),
        ('MEMCACHED', 'Memcached'),
        ('FILESYSTEM', 'File System Cache'),
        ('DATABASE', 'Database Cache'),
        ('DUMMY', 'Dummy Cache (Development)'),
    ]

    name = models.CharField(max_length=100)
    cache_type = models.CharField(max_length=20, choices=CACHE_TYPES, default='REDIS')
    host = models.CharField(max_length=200)
    port = models.PositiveIntegerField()
    password = EncryptedCharField(max_length=200)
    is_active = models.BooleanField(default=True)


class BackupConfiguration(models.Model):
    """Configuration for system backups"""
    BACKUP_PROVIDERS = [
        ('LOCAL', 'Local Storage'),
        ('AWS_S3', 'Amazon S3'),
        ('GCS', 'Google Cloud Storage'),
        ('AZURE', 'Azure Blob Storage'),
        ('FTP', 'FTP Server'),
        ('SFTP', 'SFTP Server'),
        ('DROPBOX', 'Dropbox'),
        ('GDRIVE', 'Google Drive'),
    ]

    name = models.CharField(max_length=100)
    backup_provider = models.CharField(max_length=20, choices=BACKUP_PROVIDERS, default='LOCAL')
    schedule = models.JSONField()
    retention_policy = models.JSONField()
    encryption_key = EncryptedCharField(max_length=200)
    is_active = models.BooleanField(default=True)

#------------------------------------------------------------------------------
# Storage and File Management Models
#------------------------------------------------------------------------------

class CloudStorageProvider(models.Model):
    """Configuration for cloud storage providers"""
    PROVIDER_TYPES = [
        ('AWS_S3', 'Amazon S3'),
        ('GCS', 'Google Cloud Storage'),
        ('AZURE_BLOB', 'Azure Blob Storage'),
        ('DIGITAL_OCEAN', 'Digital Ocean Spaces'),
        ('CLOUDINARY', 'Cloudinary'),
        ('LOCAL', 'Local Storage'),
    ]

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    access_key = EncryptedCharField(max_length=200)
    secret_key = EncryptedCharField(max_length=200)
    bucket_name = models.CharField(max_length=100)
    region = models.CharField(max_length=50, blank=True)
    endpoint_url = models.URLField(blank=True)
    base_url = models.URLField()
    max_file_size = models.PositiveIntegerField()
    allowed_file_types = models.JSONField(default=list)
    custom_headers = models.JSONField(default=dict, blank=True)
    cors_configuration = models.JSONField(default=dict, blank=True)

#------------------------------------------------------------------------------
# Communication Settings Models
#------------------------------------------------------------------------------

class EmailConfiguration(models.Model):
    """Email service provider configurations"""
    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=50,
        choices=[
            ('SMTP', 'SMTP'),
            ('AWS_SES', 'Amazon SES'),
            ('SENDGRID', 'SendGrid'),
            ('MAILGUN', 'Mailgun'),
            ('POSTMARK', 'Postmark'),
            ('CUSTOM', 'Custom SMTP'),
        ]
    )
    host = EncryptedCharField(max_length=200)
    port = models.IntegerField()
    username = EncryptedCharField(max_length=200)
    password = EncryptedCharField(max_length=200)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)


class SMSProvider(models.Model):
    """Configuration for SMS service providers"""
    PROVIDER_TYPES = [
        ('TWILIO', 'Twilio'),
        ('MSG91', 'MSG91'),
        ('AWS_SNS', 'Amazon SNS'),
        ('KALEYRA', 'Kaleyra'),
        ('CUSTOM', 'Custom Provider'),
    ]

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    account_sid = EncryptedCharField(max_length=200, blank=True)
    auth_token = EncryptedCharField(max_length=200)
    sender_id = models.CharField(max_length=20)
    api_endpoint = models.URLField(blank=True)
    webhook_url = models.URLField(blank=True)
    supports_unicode = models.BooleanField(default=True)
    supports_delivery_reports = models.BooleanField(default=True)
    max_message_length = models.PositiveIntegerField(default=160)
    rate_limit = models.PositiveIntegerField(null=True, blank=True)


class NotificationProvider(models.Model):
    """Configuration for push notification services"""
    PROVIDER_TYPES = [
        ('FCM', 'Firebase Cloud Messaging'),
        ('APNS', 'Apple Push Notification Service'),
        ('ONESIGNAL', 'OneSignal'),
        ('CUSTOM', 'Custom Provider'),
    ]

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    is_active = models.BooleanField(default=True)
    api_key = EncryptedCharField(max_length=200)
    app_id = models.CharField(max_length=200, blank=True)
    team_id = models.CharField(max_length=200, blank=True)
    environment = models.CharField(
        max_length=20,
        choices=[('development', 'Development'), ('production', 'Production')],
        default='development'
    )
    certificate_path = models.CharField(max_length=255, blank=True)
    supports_rich_media = models.BooleanField(default=False)
    max_payload_size = models.PositiveIntegerField(default=4096)

#------------------------------------------------------------------------------
# Payment and Financial Settings Models
#------------------------------------------------------------------------------

class PaymentGateway(models.Model):
    """Configuration for payment gateways"""
    GATEWAY_TYPES = [
        ('RAZORPAY', 'Razorpay'),
        ('STRIPE', 'Stripe'),
        ('PAYPAL', 'PayPal'),
        ('PAYTM', 'Paytm'),
        ('PHONEPE', 'PhonePe'),
        ('UPI', 'UPI'),
    ]

    name = models.CharField(max_length=100)
    gateway_type = models.CharField(max_length=20, choices=GATEWAY_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    api_key = EncryptedCharField(max_length=200)
    api_secret = EncryptedCharField(max_length=200)
    merchant_id = EncryptedCharField(max_length=200, blank=True)
    environment = models.CharField(
        max_length=20,
        choices=[('sandbox', 'Sandbox'), ('production', 'Production')],
        default='sandbox'
    )
    webhook_secret = EncryptedCharField(max_length=200, blank=True)
    webhook_url = models.URLField(blank=True)
    supported_currencies = models.JSONField(default=list)
    transaction_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    settlement_period_days = models.PositiveIntegerField(default=3)

#------------------------------------------------------------------------------
# Integration and API Settings Models
#------------------------------------------------------------------------------

class APIConfiguration(models.Model):
    """Configuration for external API integrations"""
    AUTH_TYPES = [
            ('API_KEY', 'API Key'),
            ('OAUTH2', 'OAuth 2.0'),
            ('JWT', 'JWT'),
            ('BASIC', 'Basic Auth'),
    ]
    name = models.CharField(max_length=100)
    api_url = models.URLField()
    version = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    auth_type = models.CharField(
        max_length=20,
        choices=AUTH_TYPES
    )
    api_key = EncryptedCharField(max_length=200, blank=True)
    client_id = EncryptedCharField(max_length=200, blank=True)
    client_secret = EncryptedCharField(max_length=200, blank=True)
    timeout_seconds = models.PositiveIntegerField(default=30)
    retry_attempts = models.PositiveIntegerField(default=3)
    rate_limit = models.JSONField(default=dict, blank=True)
    custom_headers = models.JSONField(default=dict, blank=True)


class SocialMediaCredential(models.Model):
    """Credentials for various social media platforms"""
    PLATFORM_CHOICES = [
        ('FACEBOOK', 'Facebook'),
        ('INSTAGRAM', 'Instagram'),
        ('WHATSAPP', 'WhatsApp'),
        ('TWITTER', 'Twitter'),
        ('LINKEDIN', 'LinkedIn'),
        ('YOUTUBE', 'YouTube'),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    app_id = EncryptedCharField(max_length=200, blank=True)
    app_secret = EncryptedCharField(max_length=200, blank=True)
    access_token = EncryptedTextField(blank=True)
    refresh_token = EncryptedTextField(blank=True)
    webhook_secret = EncryptedCharField(max_length=200, blank=True)
    verify_token = EncryptedCharField(max_length=200, blank=True)
    business_account_id = models.CharField(max_length=200, blank=True)
    phone_number_id = models.CharField(max_length=200, blank=True)
    additional_settings = models.JSONField(
        null=True,
        blank=True,
        help_text="Platform-specific additional settings"
    )
    environment = models.CharField(
        max_length=20,
        choices=[
            ('development', 'Development'),
            ('staging', 'Staging'),
            ('production', 'Production'),
        ],
        default='development'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_social_credentials'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_social_credentials'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['platform', 'environment']

    def __str__(self):
        return f"{self.platform} Credentials ({self.environment})"


#------------------------------------------------------------------------------
# Security and Authentication Settings Models
#------------------------------------------------------------------------------

class SecurityConfiguration(models.Model):
    """Global security settings and policies"""
    password_policy = models.JSONField(
        default=dict,
        help_text="Password requirements and restrictions"
    )
    ip_whitelist = models.JSONField(
        default=list,
        help_text="List of allowed IP addresses"
    )
    max_session_duration = models.PositiveIntegerField(
        default=3600,
        help_text="Maximum session duration in seconds"
    )
    jwt_secret_key = EncryptedCharField(max_length=200)
    jwt_expiry_hours = models.PositiveIntegerField(default=24)
    enable_rate_limiting = models.BooleanField(default=True)
    rate_limit_config = models.JSONField(default=dict)
    cors_allowed_origins = models.JSONField(default=list)
    enable_audit_trail = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Security Configuration"
        verbose_name_plural = "Security Configurations"


class AuthenticationProvider(models.Model):
    """Configuration for external authentication providers"""
    PROVIDER_TYPES = [
        ('OAUTH2', 'OAuth 2.0'),
        ('SAML', 'SAML'),
        ('LDAP', 'LDAP'),
        ('ACTIVE_DIRECTORY', 'Active Directory'),
        ('CUSTOM', 'Custom Provider'),
    ]

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    client_id = EncryptedCharField(max_length=200, blank=True)
    client_secret = EncryptedCharField(max_length=200, blank=True)
    authorization_url = models.URLField(blank=True)
    token_url = models.URLField(blank=True)
    userinfo_url = models.URLField(blank=True)
    scope = models.CharField(max_length=200, blank=True)
    additional_settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Authentication Provider"
        verbose_name_plural = "Authentication Providers"


#------------------------------------------------------------------------------
# Monitoring and Analytics Settings Models
#------------------------------------------------------------------------------

class MonitoringConfiguration(models.Model):
    """Configuration for system monitoring and analytics"""
    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=50,
        choices=[
            ('PROMETHEUS', 'Prometheus'),
            ('GRAFANA', 'Grafana'),
            ('DATADOG', 'Datadog'),
            ('NEW_RELIC', 'New Relic'),
            ('CUSTOM', 'Custom Solution'),
        ]
    )
    api_key = EncryptedCharField(max_length=200, blank=True)
    endpoint_url = models.URLField(blank=True)
    metrics_config = models.JSONField(default=dict)
    alert_config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Monitoring Configuration"
        verbose_name_plural = "Monitoring Configurations"


class AnalyticsConfiguration(models.Model):
    """Configuration for analytics and tracking"""
    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=50,
        choices=[
            ('GOOGLE_ANALYTICS', 'Google Analytics'),
            ('MIXPANEL', 'Mixpanel'),
            ('CUSTOM', 'Custom Analytics'),
        ]
    )
    tracking_id = models.CharField(max_length=100)
    api_key = EncryptedCharField(max_length=200, blank=True)
    additional_settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Analytics Configuration"
        verbose_name_plural = "Analytics Configurations"