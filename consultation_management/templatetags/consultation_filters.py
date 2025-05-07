from django import template

register = template.Library()

@register.filter(name='split')
def split_filter(value, arg):
    return value.split(arg)

@register.filter(name='status_badge_class')
def status_badge_class(status):
    classes = {
        'SCHEDULED': 'bg-yellow-100 text-yellow-800',
        'IN_PROGRESS': 'bg-blue-100 text-blue-800',
        'COMPLETED': 'bg-green-100 text-green-800',
        'CANCELLED': 'bg-red-100 text-red-800',
        'NO_SHOW': 'bg-gray-100 text-gray-800'
    }
    return classes.get(status, 'bg-gray-100 text-gray-800')