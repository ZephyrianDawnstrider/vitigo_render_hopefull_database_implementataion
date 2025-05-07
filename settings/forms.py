# settings/forms.py

from django import forms
import json
import pytz
from .models import SettingCategory, SettingDefinition, Setting, SystemConfiguration, LoggingConfiguration, CacheConfiguration, BackupConfiguration, CloudStorageProvider, EmailConfiguration, SMSProvider, NotificationProvider, PaymentGateway, APIConfiguration, SocialMediaCredential, SecurityConfiguration, AuthenticationProvider, AnalyticsConfiguration, MonitoringConfiguration

class SettingCategoryForm(forms.ModelForm):
    name = forms.CharField(
        help_text='Display name for the settings category'
    )
    key = forms.CharField(
        help_text='Unique identifier for the category (no spaces allowed)'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Detailed description of what this category encompasses'
    )
    icon = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'fa-cog'}),
        help_text='Font Awesome icon class (e.g., fa-cog, fa-user)'
    )
    order = forms.IntegerField(
        help_text='Display order of the category (lower numbers appear first)'
    )
    is_active = forms.BooleanField(
        required=False,
        help_text='Whether this category is currently active'
    )
    parent = forms.ModelChoiceField(
        queryset=SettingCategory.objects.all(),
        required=False,
        help_text='Parent category if this is a sub-category'
    )

    class Meta:
        model = SettingCategory
        fields = ['name', 'key', 'description', 'icon', 'order', 'is_active', 'parent']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'icon': forms.TextInput(attrs={'placeholder': 'fa-cog'}),
        }

    def clean_key(self):
        key = self.cleaned_data['key']
        if ' ' in key:
            raise forms.ValidationError("Key cannot contain spaces")
        return key.lower()

class SettingDefinitionForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=SettingCategory.objects.all(),
        help_text='The category this setting belongs to'
    )
    name = forms.CharField(
        help_text='Display name for the setting'
    )
    key = forms.CharField(
        help_text='Unique identifier for the setting (no spaces allowed)'
    )
    setting_type = forms.ChoiceField(
        choices=SettingDefinition.SETTING_TYPES,
        help_text='The type of value this setting will store'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Detailed description of what this setting controls'
    )
    default_value = forms.CharField(
        required=False,
        help_text='Default value for this setting'
    )
    is_required = forms.BooleanField(
        required=False,
        help_text='Whether this setting must have a value'
    )
    is_sensitive = forms.BooleanField(
        required=False,
        help_text='Whether this setting contains sensitive information'
    )
    validation_regex = forms.CharField(
        required=False,
        help_text='Regular expression pattern for validating the setting value'
    )
    validation_message = forms.CharField(
        required=False,
        help_text='Custom message to display when validation fails'
    )
    possible_values = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='JSON array of possible values (e.g., ["option1", "option2"])'
    )
    order = forms.IntegerField(
        help_text='Display order of the setting (lower numbers appear first)'
    )
    is_active = forms.BooleanField(
        required=False,
        help_text='Whether this setting definition is currently active'
    )

    class Meta:
        model = SettingDefinition
        fields = ['category', 'name', 'key', 'setting_type', 'description', 
                 'default_value', 'is_required', 'is_sensitive', 
                 'validation_regex', 'validation_message', 'possible_values', 
                 'order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'validation_message': forms.TextInput(),
            'possible_values': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_key(self):
        key = self.cleaned_data['key']
        if ' ' in key:
            raise forms.ValidationError("Key cannot contain spaces")
        return key.lower()

    def clean_possible_values(self):
        possible_values = self.cleaned_data.get('possible_values')
        if possible_values:
            try:
                return json.loads(possible_values)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format")
        return None

class SystemConfigurationForm(forms.ModelForm):
    site_name = forms.CharField(
        help_text='The name of your site that will be displayed to users'
    )
    site_url = forms.URLField(
        help_text='The main URL of your application (must start with http:// or https://)'
    )
    admin_email = forms.EmailField(
        help_text='Primary email address for system notifications and alerts'
    )
    session_timeout_minutes = forms.IntegerField(
        help_text='How long until an inactive user session expires (in minutes)'
    )
    password_expiry_days = forms.IntegerField(
        help_text='Number of days before users must change their password (0 for never)'
    )
    max_login_attempts = forms.IntegerField(
        help_text='Number of failed login attempts before account lockout'
    )
    require_2fa = forms.BooleanField(
        required=False,
        help_text='Require two-factor authentication for all users'
    )
    max_upload_size_mb = forms.IntegerField(
        help_text='Maximum file upload size allowed in megabytes'
    )
    allowed_file_extensions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='JSON array of allowed file extensions (e.g., [".pdf", ".jpg", ".png"])'
    )
    default_timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Default timezone for displaying dates and times'
    )
    default_language = forms.CharField(
        help_text='Default language code for the application (e.g., en-us, fr-fr)'
    )
    date_format = forms.CharField(
        help_text='Default date format (e.g., YYYY-MM-DD, DD/MM/YYYY)'
    )
    time_format = forms.CharField(
        help_text='Default time format (e.g., HH:mm:ss, hh:mm A)'
    )
    business_hours = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='JSON object defining business hours for each day (e.g., {"monday": {"start": "09:00", "end": "17:00"}})'
    )
    holiday_calendar = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='JSON array of holiday dates and descriptions'
    )
    appointment_duration_minutes = forms.IntegerField(
        help_text='Default duration for appointments in minutes'
    )

    class Meta:
        model = SystemConfiguration
        fields = ['site_name', 'site_url', 'admin_email', 'session_timeout_minutes',
                 'password_expiry_days', 'max_login_attempts', 'require_2fa',
                 'max_upload_size_mb', 'allowed_file_extensions', 'default_timezone',
                 'default_language', 'date_format', 'time_format', 'business_hours',
                 'holiday_calendar', 'appointment_duration_minutes']

    def clean_site_url(self):
        url = self.cleaned_data['site_url']
        if not url.startswith(('http://', 'https://')):
            raise forms.ValidationError("URL must start with http:// or https://")
        return url

    def clean_allowed_file_extensions(self):
        value = self.cleaned_data.get('allowed_file_extensions')
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format")
        return None

    def clean_business_hours(self):
        value = self.cleaned_data.get('business_hours')
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format")
        return None

    def clean_holiday_calendar(self):
        value = self.cleaned_data.get('holiday_calendar')
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format")
        return None

class SettingValueForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = ['value', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.definition:
            if self.instance.definition.setting_type == 'BOOLEAN':
                self.fields['value'] = forms.BooleanField(required=False)
            elif self.instance.definition.setting_type == 'NUMBER':
                self.fields['value'] = forms.FloatField()
            elif self.instance.definition.setting_type == 'JSON':
                self.fields['value'] = forms.JSONField()
            elif self.instance.definition.setting_type == 'EMAIL':
                self.fields['value'] = forms.EmailField()
            elif self.instance.definition.setting_type == 'URL':
                self.fields['value'] = forms.URLField()


class LoggingConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='Identifier for this logging configuration'
    )
    log_level = forms.ChoiceField(
        choices=LoggingConfiguration.LOG_LEVELS,
        help_text='Severity level of logs to capture (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
    )
    log_file_path = forms.CharField(
        help_text='Absolute path where log files will be stored'
    )
    rotation_policy = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '''{
                "max_bytes": 10485760,
                "backup_count": 5,
                "compress": true,
                "when": "midnight",
                "interval": 1
            }''',
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'
        }),
        help_text='JSON policy for log rotation. Example: max_bytes (bytes before rotation), backup_count (number of backups), compress (true/false), when (rotation timing), interval (rotation frequency)'
    )
    retention_days = forms.IntegerField(
        help_text='Number of days to keep log files before deletion'
    )
    is_active = forms.BooleanField(
        required=False,
        help_text='Whether this logging configuration is currently active'
    )

    class Meta:
        model = LoggingConfiguration
        fields = ['name', 'log_level', 'log_file_path', 'rotation_policy', 'retention_days', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'log_level': forms.Select(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'log_file_path': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'rotation_policy': forms.Textarea(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5', 'rows': 3}),
            'retention_days': forms.NumberInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500'}),
        }

    def clean_rotation_policy(self):
        rotation_policy = self.cleaned_data.get('rotation_policy')
        if rotation_policy:
            try:
                policy = json.loads(rotation_policy)
                # Validate required fields
                required_fields = ['max_bytes', 'backup_count']
                for field in required_fields:
                    if field not in policy:
                        raise forms.ValidationError(f"Missing required field: {field}")
                
                # Validate field types
                if not isinstance(policy.get('max_bytes'), int):
                    raise forms.ValidationError("max_bytes must be an integer")
                if not isinstance(policy.get('backup_count'), int):
                    raise forms.ValidationError("backup_count must be an integer")
                if 'compress' in policy and not isinstance(policy['compress'], bool):
                    raise forms.ValidationError("compress must be a boolean")
                
                return policy
            except json.JSONDecodeError as e:
                raise forms.ValidationError(f"Invalid JSON format: {str(e)}")
        return None

class CacheConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='Identifier for this cache configuration'
    )
    cache_type = forms.ChoiceField(
        choices=CacheConfiguration.CACHE_TYPES,
        help_text='Type of cache backend to use for the application'
    )
    host = forms.CharField(
        help_text='Hostname or IP address of the cache server'
    )
    port = forms.IntegerField(
        help_text='Port number on which the cache server is running'
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text='Authentication password for the cache server (if required)',
        required=False
    )
    is_active = forms.BooleanField(
        required=False,
        help_text='Whether this cache configuration is currently active'
    )

    class Meta:
        model = CacheConfiguration
        fields = ['name', 'cache_type', 'host', 'port', 'password', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'cache_type': forms.Select(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'host': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'port': forms.NumberInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'password': forms.PasswordInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500'}),
        }

class BackupConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='Identifier for this backup configuration'
    )
    backup_provider = forms.ChoiceField(
        choices=BackupConfiguration.BACKUP_PROVIDERS,
        help_text='Service provider where backups will be stored'
    )
    schedule = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='JSON schedule for backup runs (e.g., {"frequency": "daily", "time": "02:00"}, or cron expression)'
    )
    retention_policy = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='JSON policy for backup retention (e.g., {"daily": 7, "weekly": 4, "monthly": 3})'
    )
    encryption_key = forms.CharField(
        widget=forms.PasswordInput,
        help_text='Encryption key for securing backup data (stored securely)',
        required=False
    )
    is_active = forms.BooleanField(
        required=False,
        help_text='Whether this backup configuration is currently active'
    )

    class Meta:
        model = BackupConfiguration
        fields = ['name', 'backup_provider', 'schedule', 'retention_policy', 'encryption_key', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'backup_provider': forms.Select(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'schedule': forms.Textarea(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5', 'rows': 3}),
            'retention_policy': forms.Textarea(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5', 'rows': 3}),
            'encryption_key': forms.PasswordInput(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500'}),
        }

    def clean_schedule(self):
        schedule = self.cleaned_data.get('schedule')
        if schedule:
            try:
                return json.loads(schedule)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for schedule")
        return None

    def clean_retention_policy(self):
        retention_policy = self.cleaned_data.get('retention_policy')
        if retention_policy:
            try:
                return json.loads(retention_policy)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for retention policy")
        return None

class CloudStorageProviderForm(forms.ModelForm):
    name = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., AWS Production Storage',
            'class': 'form-control'
        }),
        help_text='Enter a name for this storage configuration'
    )
    provider_type = forms.ChoiceField(
        choices=CloudStorageProvider.PROVIDER_TYPES,
        help_text='Select your cloud storage provider'
    )
    access_key = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your access key',
            'class': 'form-control'
        }),
        help_text='Enter the access key provided by your storage provider'
    )
    secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your secret key',
            'class': 'form-control'
        }),
        help_text='Enter the secret key provided by your storage provider'
    )
    bucket_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., my-app-storage',
            'class': 'form-control'
        }),
        help_text='Enter your storage bucket or container name'
    )
    region = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., us-east-1',
            'class': 'form-control'
        }),
        help_text='Enter the region (e.g., us-east-1) - optional'
    )
    endpoint_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'https://custom-endpoint.com',
            'class': 'form-control'
        }),
        help_text='Custom endpoint URL - optional'
    )
    base_url = forms.URLField(
        widget=forms.URLInput(attrs={
            'placeholder': 'https://your-storage.com/files',
            'class': 'form-control'
        }),
        help_text='Base URL for accessing your stored files'
    )
    max_file_size = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'placeholder': '5242880',
            'class': 'form-control'
        }),
        help_text='Maximum file size in bytes (e.g., 5242880 for 5MB)'
    )
    allowed_file_types = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '[".jpg", ".png", ".pdf", ".doc"]',
            'class': 'form-control'
        }),
        help_text='List of allowed file types in JSON array format'
    )
    custom_headers = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{\n  "Cache-Control": "max-age=86400",\n  "x-custom-header": "value"\n}',
            'class': 'form-control'
        }),
        required=False,
        help_text='Custom headers in JSON format - optional'
    )
    cors_configuration = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{\n  "allowed_origins": ["*"],\n  "allowed_methods": ["GET", "POST"],\n  "max_age_seconds": 3600\n}',
            'class': 'form-control'
        }),
        required=False,
        help_text='CORS settings in JSON format - optional'
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Check to activate this storage provider'
    )
    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Set as the default storage provider'
    )

    class Meta:
        model = CloudStorageProvider
        fields = ['name', 'provider_type', 'access_key', 'secret_key', 
                 'bucket_name', 'region', 'endpoint_url', 'base_url',
                 'max_file_size', 'allowed_file_types', 'custom_headers',
                 'cors_configuration', 'is_active', 'is_default']

class EmailConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this email configuration',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Company Gmail'})
    )
    provider = forms.ChoiceField(
        choices=EmailConfiguration.provider.field.choices,
        help_text='Select your email service provider'
    )
    host = forms.CharField(
        help_text='SMTP server hostname',
        widget=forms.TextInput(attrs={'placeholder': 'smtp.gmail.com'})
    )
    port = forms.IntegerField(
        help_text='SMTP server port (usually 587 for TLS, 465 for SSL)',
        widget=forms.NumberInput(attrs={'placeholder': '587'})
    )
    username = forms.CharField(
        help_text='Email account username or address',
        widget=forms.TextInput(attrs={'placeholder': 'your@email.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Email account password or app-specific password'
    )
    from_email = forms.EmailField(
        help_text='Default sender email address',
        widget=forms.EmailInput(attrs={'placeholder': 'noreply@yourcompany.com'})
    )
    from_name = forms.CharField(
        help_text='Default sender name',
        widget=forms.TextInput(attrs={'placeholder': 'Your Company Name'})
    )

    class Meta:
        model = EmailConfiguration
        fields = ['name', 'provider', 'host', 'port', 'username', 'password',
                 'use_tls', 'use_ssl', 'from_email', 'from_name', 'is_active',
                 'is_default']
        help_texts = {
            'use_tls': 'Use TLS encryption for secure connection',
            'use_ssl': 'Use SSL encryption for secure connection',
            'is_active': 'Enable/disable this email configuration',
            'is_default': 'Set as the default email provider'
        }

class SMSProviderForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this SMS provider',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Twilio Main'})
    )
    provider_type = forms.ChoiceField(
        choices=SMSProvider.PROVIDER_TYPES,
        help_text='Select your SMS service provider'
    )
    account_sid = forms.CharField(
        help_text='Your provider account identifier',
        widget=forms.TextInput(attrs={'placeholder': 'Enter account SID/ID'})
    )
    auth_token = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Authentication token from your provider'
    )
    sender_id = forms.CharField(
        help_text='Default sender ID or phone number',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., COMPANYNAME or +1234567890'})
    )
    max_message_length = forms.IntegerField(
        help_text='Maximum characters per message',
        initial=160,
        widget=forms.NumberInput(attrs={'placeholder': '160'})
    )

    class Meta:
        model = SMSProvider
        fields = ['name', 'provider_type', 'account_sid', 'auth_token',
                 'sender_id', 'api_endpoint', 'webhook_url', 'supports_unicode',
                 'supports_delivery_reports', 'max_message_length', 'rate_limit',
                 'is_active', 'is_default']
        help_texts = {
            'api_endpoint': 'Custom API endpoint URL (if required)',
            'webhook_url': 'URL for delivery status notifications',
            'supports_unicode': 'Enable support for special characters',
            'supports_delivery_reports': 'Enable delivery status tracking',
            'rate_limit': 'Maximum messages per second (if applicable)',
            'is_active': 'Enable/disable this SMS provider',
            'is_default': 'Set as the default SMS provider'
        }
        widgets = {
            'api_endpoint': forms.URLInput(attrs={'placeholder': 'https://api.provider.com'}),
            'webhook_url': forms.URLInput(attrs={'placeholder': 'https://your-domain.com/webhook'}),
            'rate_limit': forms.NumberInput(attrs={'placeholder': '10'})
        }

class NotificationProviderForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this notification service',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Firebase Push'})
    )
    provider_type = forms.ChoiceField(
        choices=NotificationProvider.PROVIDER_TYPES,
        help_text='Select your push notification service'
    )
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API key from your notification provider'
    )
    app_id = forms.CharField(
        help_text='Application identifier',
        widget=forms.TextInput(attrs={'placeholder': 'Your app ID'}),
        required=False
    )
    max_payload_size = forms.IntegerField(
        help_text='Maximum notification payload size in bytes',
        initial=4096,
        widget=forms.NumberInput(attrs={'placeholder': '4096'})
    )

    class Meta:
        model = NotificationProvider
        fields = ['name', 'provider_type', 'api_key', 'app_id', 'team_id',
                 'environment', 'certificate_path', 'supports_rich_media',
                 'max_payload_size', 'is_active']
        help_texts = {
            'team_id': 'Team identifier (required for some providers)',
            'environment': 'Select deployment environment',
            'certificate_path': 'Path to certificate file (if required)',
            'supports_rich_media': 'Enable rich media notifications',
            'is_active': 'Enable/disable this notification provider'
        }
        widgets = {
            'team_id': forms.TextInput(attrs={'placeholder': 'Your team ID'}),
            'certificate_path': forms.TextInput(attrs={'placeholder': '/path/to/certificate.pem'})
        }

class PaymentGatewayForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this payment gateway',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Razorpay Production'})
    )
    gateway_type = forms.ChoiceField(
        choices=PaymentGateway.GATEWAY_TYPES,
        help_text='Select your payment gateway provider'
    )
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API key from your payment provider'
    )
    api_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API secret from your payment provider'
    )
    merchant_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Your merchant ID'}),
        help_text='Merchant ID (if required by provider)'
    )
    webhook_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Webhook signing secret for verifying callbacks'
    )
    webhook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://your-domain.com/webhooks/payment'}),
        help_text='URL where provider will send payment notifications'
    )
    transaction_fee_percentage = forms.DecimalField(
        help_text='Transaction fee charged by the provider (%)',
        widget=forms.NumberInput(attrs={'placeholder': '2.5'})
    )
    settlement_period_days = forms.IntegerField(
        help_text='Number of days for settlement',
        widget=forms.NumberInput(attrs={'placeholder': '3'})
    )

    class Meta:
        model = PaymentGateway
        fields = ['name', 'gateway_type', 'api_key', 'api_secret', 'merchant_id',
                 'environment', 'webhook_secret', 'webhook_url', 
                 'supported_currencies', 'transaction_fee_percentage',
                 'settlement_period_days', 'is_active', 'is_default']
        help_texts = {
            'environment': 'Select deployment environment (sandbox/production)',
            'supported_currencies': 'List of supported currency codes',
            'is_active': 'Enable/disable this payment gateway',
            'is_default': 'Set as the default payment gateway'
        }

    def clean_supported_currencies(self):
        currencies = self.cleaned_data.get('supported_currencies')
        if isinstance(currencies, str):
            try:
                return json.loads(currencies)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for supported currencies")
        return currencies

class APIConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this API integration',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Payment API'})
    )
    api_url = forms.URLField(
        help_text='Base URL of the API',
        widget=forms.URLInput(attrs={'placeholder': 'https://api.example.com/v1'})
    )
    version = forms.CharField(
        help_text='API version (e.g., v1, v2)',
        widget=forms.TextInput(attrs={'placeholder': 'v1'})
    )
    auth_type = forms.ChoiceField(
        choices=APIConfiguration.AUTH_TYPES,
        help_text='Authentication method used by the API'
    )
    api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API key (if using API key authentication)'
    )
    client_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Your client ID'}),
        help_text='OAuth client ID'
    )
    client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='OAuth client secret'
    )

    class Meta:
        model = APIConfiguration
        fields = ['name', 'api_url', 'version', 'auth_type', 'api_key',
                 'client_id', 'client_secret', 'timeout_seconds',
                 'retry_attempts', 'rate_limit', 'custom_headers', 'is_active']
        help_texts = {
            'timeout_seconds': 'Request timeout in seconds',
            'retry_attempts': 'Number of retry attempts for failed requests',
            'rate_limit': 'Rate limiting configuration (JSON)',
            'custom_headers': 'Custom headers to include in requests (JSON)',
            'is_active': 'Enable/disable this API configuration'
        }

class SocialMediaCredentialForm(forms.ModelForm):
    platform = forms.ChoiceField(
        choices=SocialMediaCredential.PLATFORM_CHOICES,
        help_text='Select social media platform'
    )
    app_id = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Application ID from the platform'
    )
    app_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Application secret from the platform'
    )
    access_token = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=False,
        help_text='OAuth access token'
    )
    refresh_token = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        required=False,
        help_text='OAuth refresh token'
    )

    class Meta:
        model = SocialMediaCredential
        fields = ['platform', 'app_id', 'app_secret', 'access_token',
                 'refresh_token', 'webhook_secret', 'verify_token',
                 'business_account_id', 'phone_number_id',
                 'additional_settings', 'environment', 'is_active']
        help_texts = {
            'webhook_secret': 'Webhook signing secret',
            'verify_token': 'Webhook verification token',
            'business_account_id': 'Business account ID (if applicable)',
            'phone_number_id': 'Phone number ID (for WhatsApp)',
            'additional_settings': 'Additional platform-specific settings (JSON)',
            'environment': 'Select deployment environment',
            'is_active': 'Enable/disable these credentials'
        }

class SecurityConfigurationForm(forms.ModelForm):
    password_policy = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '{"min_length": 8, "require_special": true}'}),
        help_text='JSON object defining password requirements'
    )
    ip_whitelist = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '["192.168.1.1", "10.0.0.0/24"]'}),
        help_text='JSON array of allowed IP addresses/ranges'
    )
    max_session_duration = forms.IntegerField(
        help_text='Maximum session duration in seconds',
        widget=forms.NumberInput(attrs={'placeholder': '3600'})
    )
    jwt_secret_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Secret key for JWT token signing'
    )
    jwt_expiry_hours = forms.IntegerField(
        help_text='JWT token expiry time in hours',
        widget=forms.NumberInput(attrs={'placeholder': '24'})
    )
    rate_limit_config = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '{"requests": 100, "period": 60}'}),
        help_text='JSON object defining rate limiting rules'
    )
    cors_allowed_origins = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '["https://example.com"]'}),
        help_text='JSON array of allowed CORS origins'
    )

    class Meta:
        model = SecurityConfiguration
        fields = ['password_policy', 'ip_whitelist', 'max_session_duration',
                 'jwt_secret_key', 'jwt_expiry_hours', 'enable_rate_limiting',
                 'rate_limit_config', 'cors_allowed_origins', 'enable_audit_trail']

class AuthenticationProviderForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this provider',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Google OAuth'})
    )
    provider_type = forms.ChoiceField(
        choices=AuthenticationProvider.PROVIDER_TYPES,
        help_text='Select the authentication provider type'
    )
    client_id = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Client ID from your auth provider'
    )
    client_secret = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='Client secret from your auth provider'
    )
    authorization_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://provider.com/auth'}),
        help_text='Authorization endpoint URL'
    )
    token_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://provider.com/token'}),
        help_text='Token endpoint URL'
    )

    class Meta:
        model = AuthenticationProvider
        fields = ['name', 'provider_type', 'client_id', 'client_secret',
                 'authorization_url', 'token_url', 'userinfo_url', 'scope',
                 'additional_settings', 'is_active', 'is_default']
        help_texts = {
            'userinfo_url': 'User info endpoint URL',
            'scope': 'OAuth scopes (space-separated)',
            'additional_settings': 'Additional provider-specific settings (JSON)',
            'is_active': 'Enable/disable this provider',
            'is_default': 'Set as the default provider'
        }

class MonitoringConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this monitoring configuration',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Production Metrics'})
    )
    provider = forms.ChoiceField(
        choices=MonitoringConfiguration.provider.field.choices,
        help_text='Select your monitoring service provider'
    )
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API key from your monitoring provider'
    )
    endpoint_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://monitoring.provider.com'}),
        help_text='Monitoring service endpoint URL'
    )
    metrics_config = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{\n  "collect_interval": 60,\n  "metrics": ["cpu", "memory", "disk"]\n}'
        }),
        help_text='JSON configuration for metrics collection'
    )
    alert_config = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{\n  "thresholds": {"cpu": 80, "memory": 90},\n  "notify": ["email", "slack"]\n}'
        }),
        help_text='JSON configuration for alerts'
    )

    class Meta:
        model = MonitoringConfiguration
        fields = ['name', 'provider', 'api_key', 'endpoint_url',
                 'metrics_config', 'alert_config', 'is_active']

class AnalyticsConfigurationForm(forms.ModelForm):
    name = forms.CharField(
        help_text='A friendly name to identify this analytics configuration',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Google Analytics Web'})
    )
    provider = forms.ChoiceField(
        choices=AnalyticsConfiguration.provider.field.choices,
        help_text='Select your analytics provider'
    )
    tracking_id = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'UA-XXXXX-Y or G-XXXXXXX'}),
        help_text='Tracking ID/Measurement ID from your analytics provider'
    )
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text='API key for accessing analytics data'
    )
    additional_settings = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': '{\n  "anonymize_ip": true,\n  "demographic_data": false\n}'
        }),
        help_text='Additional provider-specific settings (JSON)'
    )

    class Meta:
        model = AnalyticsConfiguration
        fields = ['name', 'provider', 'tracking_id', 'api_key',
                 'additional_settings', 'is_active']