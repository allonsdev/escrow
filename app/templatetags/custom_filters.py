from django import template

register = template.Library()

@register.filter
def split(value, delimiter):
    """
    Splits a string by the given delimiter.
    Usage: {{ value|split:" " }}
    """
    if value is None:
        return []
    return value.split(delimiter)