from django import template

register = template.Library()


@register.filter
def percentage_color(value):
    """رنگ بر اساس درصد"""
    if value is None:
        return 'info'
    if value >= 75:
        return 'success'
    if value >= 50:
        return 'warning'
    return 'danger'


@register.filter
def severity_icon(value):
    """آیکون بر اساس شدت"""
    icons = {
        'CRITICAL': 'bi-exclamation-octagon-fill',
        'WARNING': 'bi-exclamation-triangle-fill',
        'INFO': 'bi-info-circle-fill',
    }
    return icons.get(value, 'bi-info-circle-fill')