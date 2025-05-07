import json
import logging
import os
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.core.serializers import serialize

from settings.models import (
    Setting, SettingCategory, SettingDefinition, SystemConfiguration,
    EmailConfiguration, SMSProvider, NotificationProvider,
    PaymentGateway, APIConfiguration
)
from access_control.permissions import PermissionManager

logger = logging.getLogger(__name__)

def create_backup():
    """Create a backup of all settings"""
    try:
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'settings': json.loads(serialize('json', Setting.objects.all())),
            'categories': json.loads(serialize('json', SettingCategory.objects.all())),
            'definitions': json.loads(serialize('json', SettingDefinition.objects.all())),
            'system_config': json.loads(serialize('json', SystemConfiguration.objects.all())),
            'email_config': json.loads(serialize('json', EmailConfiguration.objects.all())),
            'sms_config': json.loads(serialize('json', SMSProvider.objects.all())),
            'notification_config': json.loads(serialize('json', NotificationProvider.objects.all())),
            'payment_config': json.loads(serialize('json', PaymentGateway.objects.all())),
            'api_config': json.loads(serialize('json', APIConfiguration.objects.all())),
        }

        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups', 'settings')
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        filename = f"settings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(backup_dir, filename)

        # Write backup to file
        with open(filepath, 'w') as f:
            json.dump(backup_data, f, indent=4)

        return {
            'success': True,
            'filename': filename,
            'filepath': filepath
        }

    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@login_required
@csrf_protect
@require_POST
def backup_settings(request):
    """Handle settings backup request"""
    try:
        if not PermissionManager.check_module_access(request.user, 'settings'):
            messages.error(request, "You don't have permission to backup settings")
            return redirect('settings:settings_dashboard')

        backup_result = create_backup()
        
        if not backup_result['success']:
            messages.error(request, f"Backup failed: {backup_result['error']}")
            return redirect('settings:settings_dashboard')

        # Prepare file for download
        with open(backup_result['filepath'], 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="{backup_result["filename"]}"'
            
        messages.success(request, 'Settings backup created successfully')
        return response

    except Exception as e:
        logger.error(f"Settings backup error: {str(e)}")
        messages.error(request, f'Error creating backup: {str(e)}')
        return redirect('settings:settings_dashboard')
