import math
from django import template

register = template.Library()

@register.filter("or")
def num_or(s, sub):
    if (not s) or (s == 'None') or (s == '0') or (s == '0.00'):
        return sub
    else:
        return s
