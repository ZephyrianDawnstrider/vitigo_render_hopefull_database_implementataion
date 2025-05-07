import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from .exceptions import DataFetchError, StatsComputationError
from .exceptions import InvalidDateRangeError

logger = logging.getLogger(__name__)

def get_safe_division(numerator, denominator, default=0):
    """Safely divide numbers, handling zero division"""
    try:
        if not denominator:
            return default
        return (numerator / denominator)
    except Exception as e:
        logger.warning(f"Division error: {str(e)}")
        return default

def get_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    try:
        if not previous:
            return 100 if current else 0
        return ((current - previous) / previous) * 100
    except Exception as e:
        logger.warning(f"Percentage change calculation error: {str(e)}")
        return 0

def get_date_range_filter(range_type):
    """Get date range filter based on range type"""
    now = timezone.now()
    try:
        ranges = {
            'today': (now.replace(hour=0, minute=0), now),
            'week': (now - timedelta(days=7), now),
            'month': (now - timedelta(days=30), now),
            'year': (now - timedelta(days=365), now),
        }
        return ranges.get(range_type, ranges['month'])
    except Exception as e:
        logger.error(f"Date range filter error: {str(e)}")
        raise InvalidDateRangeError(f"Invalid date range: {range_type}")

def cache_dashboard_data(func):
    """Decorator to cache dashboard data"""
    def wrapper(*args, **kwargs):
        cache_key = f"dashboard_{func.__name__}_{args}_{kwargs}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
            
        data = func(*args, **kwargs)
        cache.set(cache_key, data, timeout=300)  # Cache for 5 minutes
        return data
    return wrapper

from access_control.models import Role

def get_template_path(base_template, role, module=''):
    """
    Resolves template path based on user role.
    Now uses the template_folder from Role model.
    """
    if isinstance(role, Role):
        role_folder = role.template_folder
    else:
        # Fallback for any legacy code
        role = Role.objects.get(name=role)
        role_folder = role.template_folder
    
    if module:
        return f'{role_folder}/{module}/{base_template}'
    return f'{role_folder}/{base_template}'