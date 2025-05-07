from django import template

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtract the arg from the value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='day_name')
def day_name(value):
    """Convert single letter day to full name"""
    days = {
        'M': 'Monday',
        'T': 'Tuesday',
        'W': 'Wednesday',
        'R': 'Thursday',
        'F': 'Friday',
        'S': 'Saturday',
        'U': 'Sunday'
    }
    return days.get(value, value)
