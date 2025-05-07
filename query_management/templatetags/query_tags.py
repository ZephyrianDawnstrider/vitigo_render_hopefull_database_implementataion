import os
from django import template

register = template.Library()

@register.filter(name='split')
def split(value, key):
    """
    Returns the last part of a file path
    Usage: {{ filename|split:'/' }}
    """
    return os.path.basename(value)