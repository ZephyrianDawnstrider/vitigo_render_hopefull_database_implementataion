import logging
import re
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings as django_settings  # Rename the import to avoid confusion
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

from settings.models import Setting, SettingDefinition
from access_control.permissions import PermissionManager

logger = logging.getLogger(__name__)

def validate_settings():
    """
    Validate all settings against their definitions
    """
    errors = []
    
    try:
        for setting in Setting.objects.filter(is_active=True):
            definition = setting.definition
            
            # Skip if no validation rules
            if not definition.validation_regex and not definition.possible_values:
                continue
                
            # Validate against regex if provided
            if definition.validation_regex and not re.match(definition.validation_regex, str(setting.value)):
                errors.append(f"Setting '{definition.key}' failed regex validation")
                
            # Validate against possible values if provided
            if definition.possible_values and str(setting.value) not in definition.possible_values:
                errors.append(f"Setting '{definition.key}' has invalid value")
                
    except Exception as e:
        logger.error(f"Settings validation error: {str(e)}")
        errors.append(str(e))
        
    return errors

def sync_settings_to_cache():
    """
    Synchronize settings to cache
    """
    try:
        settings_dict = {}
        for setting in Setting.objects.filter(is_active=True):
            key = f"setting_{setting.definition.key}"
            settings_dict[key] = setting.value
            
        # Store all settings in cache with prefix
        cache.set_many(settings_dict, timeout=django_settings.CACHE_TIMEOUT)
        
        return {
            'success': True,
            'timestamp': timezone.now()
        }
        
    except Exception as e:
        logger.error(f"Cache sync error: {str(e)}")
        return {
            'success': False,
            'errors': [str(e)]
        }

def sync_settings_from_db():
    """
    Synchronize settings from database
    """
    try:
        # Ensure all setting definitions have corresponding settings
        for definition in SettingDefinition.objects.filter(is_active=True):
            Setting.objects.get_or_create(
                definition=definition,
                defaults={
                    'value': definition.default_value,
                    'is_active': True
                }
            )
            
        timestamp = timezone.now()
        
        return {
            'success': True,
            'timestamp': timestamp
        }
        
    except Exception as e:
        logger.error(f"Database sync error: {str(e)}")
        return {
            'success': False,
            'errors': [str(e)]
        }


@login_required
@csrf_protect
@require_POST
def sync_settings(request):
    """
    Synchronize settings across the application
    """
    try:
        if not PermissionManager.check_module_access(request.user, 'settings'):
            messages.error(request, "You don't have permission to sync settings")
            return redirect('settings:settings_dashboard')

        # Validate current settings
        validation_errors = validate_settings()
        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect('settings:settings_dashboard')

        # Sync settings to cache
        cache_sync_result = sync_settings_to_cache()
        if not cache_sync_result['success']:
            messages.error(request, 'Cache synchronization failed')
            return redirect('settings:settings_dashboard')

        # Sync settings from database
        db_sync_result = sync_settings_from_db()
        if not db_sync_result['success']:
            messages.error(request, 'Database synchronization failed')
            return redirect('settings:settings_dashboard')

        messages.success(request, 'Settings synchronized successfully')
        return redirect('settings:settings_dashboard')

    except Exception as e:
        messages.error(request, f'Error syncing settings: {str(e)}')
        return redirect('settings:settings_dashboard')
