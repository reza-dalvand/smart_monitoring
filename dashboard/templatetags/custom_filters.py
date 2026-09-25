from django import template

register = template.Library()


@register.filter
def split(value, delimiter=','):
    """
    فیلتر سفارشی برای تقسیم رشته به لیست
    مثال: "a,b,c,d"|split:"," -> ['a', 'b', 'c', 'd']
    """
    if not value:
        return []
    return str(value).split(delimiter)