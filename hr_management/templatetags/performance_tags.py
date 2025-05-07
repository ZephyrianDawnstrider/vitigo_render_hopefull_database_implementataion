from django import template

register = template.Library()

@register.filter
def get_performance_metrics(review):
    """Convert review metrics into a list of dictionaries for template use"""
    return [
        {'name': 'Technical Skills', 'value': review.technical_skills},
        {'name': 'Communication', 'value': review.communication},
        {'name': 'Teamwork', 'value': review.teamwork},
        {'name': 'Productivity', 'value': review.productivity},
        {'name': 'Reliability', 'value': review.reliability},
    ]
