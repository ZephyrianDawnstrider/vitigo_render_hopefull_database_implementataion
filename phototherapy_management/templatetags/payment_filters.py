from django import template

register = template.Library()

@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    try:
        if not value or not arg:
            return 0
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
