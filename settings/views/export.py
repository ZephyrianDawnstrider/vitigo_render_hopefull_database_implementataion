import json
import csv
import io
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect
from django.contrib import messages
from django.core.serializers import serialize

from settings.models import (
    Setting, SettingCategory, SettingDefinition, SystemConfiguration,
    EmailConfiguration, SMSProvider, NotificationProvider,
    PaymentGateway, APIConfiguration
)
from access_control.permissions import PermissionManager

def create_json_export():
    """Create JSON export of all settings"""
    export_data = {
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
    return export_data

def create_csv_export():
    """Create CSV export of settings"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Category', 'Setting Name', 'Key', 'Value', 'Type', 'Is Active'])
    
    # Write settings data
    for setting in Setting.objects.select_related('definition', 'definition__category'):
        writer.writerow([
            setting.definition.category.name,
            setting.definition.name,
            setting.definition.key,
            setting.value,
            setting.definition.setting_type,
            setting.is_active
        ])
    
    return output.getvalue()

@login_required
@csrf_protect
@require_POST
def export_settings(request):
    """Handle settings export request"""
    try:
        if not PermissionManager.check_module_access(request.user, 'settings'):
            messages.error(request, "You don't have permission to export settings")
            return redirect('settings:settings_dashboard')

        export_format = request.POST.get('format', 'json')
        
        if export_format == 'json':
            # Create JSON export
            export_data = create_json_export()
            response = HttpResponse(
                json.dumps(export_data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = 'attachment; filename="settings_export.json"'
        
        elif export_format == 'csv':
            # Create CSV export
            csv_data = create_csv_export()
            response = HttpResponse(csv_data, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="settings_export.csv"'
        
        else:
            messages.error(request, "Invalid export format")
            return redirect('settings:settings_dashboard')

        return response

    except Exception as e:
        messages.error(request, f'Error exporting settings: {str(e)}')
        return redirect('settings:settings_dashboard')
