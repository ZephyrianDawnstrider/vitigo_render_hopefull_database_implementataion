from django import template
from django.utils.safestring import mark_safe
from datetime import timedelta

register = template.Library()

@register.filter
def split(value, key):
    """Splits the string by the given key"""
    try:
        return value.split(key)
    except Exception:
        return []

@register.filter
def attr(obj, attribute):
    """Returns an attribute of an object"""
    return getattr(obj, attribute, '')

@register.filter
def attrs(obj, attribute):
    """Returns an attribute of an object or empty string"""
    return getattr(obj, attribute, '')

@register.filter
def filter_by_type(items, type_value):
    """Filters a list of dicts or objects by 'type' attribute or key"""
    try:
        return [item for item in items if (getattr(item, 'type', None) == type_value) or (item.get('type', None) == type_value)]
    except Exception:
        return []

@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary"""
    try:
        return dictionary.get(key, '')
    except Exception:
        return ''

@register.filter
def add_days(date, days):
    """Adds days to a date"""
    try:
        return date + timedelta(days=int(days))
    except Exception:
        return date

@register.filter
def leave_filters(leaves, status):
    """Filters leaves by status"""
    try:
        return [leave for leave in leaves if getattr(leave, 'status', '') == status]
    except Exception:
        return []
