# support/templatetags/support_tags.py
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def status_badge(status):
    """Display status as a colored badge"""
    colors = {
        'open': 'bg-blue-100 text-blue-800',
        'in_progress': 'bg-yellow-100 text-yellow-800',
        'waiting_customer': 'bg-orange-100 text-orange-800',
        'resolved': 'bg-green-100 text-green-800',
        'closed': 'bg-gray-100 text-gray-800',
    }
    
    color_class = colors.get(status, 'bg-gray-100 text-gray-800')
    display_status = status.replace('_', ' ').title()
    
    return format_html(
        '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {}">{}</span>',
        color_class,
        display_status
    )

@register.filter
def priority_badge(priority):
    """Display priority as a colored badge"""
    colors = {
        'low': 'bg-gray-100 text-gray-800',
        'medium': 'bg-blue-100 text-blue-800',
        'high': 'bg-orange-100 text-orange-800',
        'urgent': 'bg-red-100 text-red-800',
    }
    
    color_class = colors.get(priority, 'bg-gray-100 text-gray-800')
    
    return format_html(
        '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {}">{}</span>',
        color_class,
        priority.title()
    )

@register.filter
def rating_stars(rating):
    """Display rating as stars"""
    if not rating:
        return ''
    
    stars = []
    for i in range(1, 6):
        if i <= rating:
            stars.append('★')
        else:
            stars.append('☆')
    
    return mark_safe(''.join(stars))