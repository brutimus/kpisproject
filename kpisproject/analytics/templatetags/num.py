import math
from django import template

register = template.Library()

@register.filter('or')
def num_or(s, sub):
    if (s is None) or (s == 'None'):
        return sub
    else:
        return s

@register.filter('percent')
def percent(s, places=0):
	try:
		return "%s%%" % int(round(s, places))
	except:
		return s

@register.filter('ratio')
def ratio(a, b):
	return float(a) / float(b) * 100