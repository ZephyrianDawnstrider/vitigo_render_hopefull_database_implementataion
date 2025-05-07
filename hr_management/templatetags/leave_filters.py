from django import template

register = template.Library()

@register.filter
def filter_by_type(settings, leave_type):
    """Filter leave settings by leave type"""
    try:
        return settings.get(leave_type=leave_type)
    except:
        return None
