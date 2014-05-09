import math
from django import template

register = template.Library()

@register.filter("or")
def num_or(s, sub):
    if (s is None) or (s == 'None'):
        return sub
    else:
        return s
