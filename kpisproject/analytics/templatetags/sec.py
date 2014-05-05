import math
from django import template

register = template.Library()

@register.filter()
def formatSeconds(s):
    if not s: return
    s = int(s)
    mins = math.floor(s / 60);
    secs = math.floor(s - (mins * 60)); 
    return "%d:%02d" % (mins, secs);
