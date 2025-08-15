from django import template
from wishlist.models import WishlistItem

register = template.Library()

@register.filter
def is_in_wishlist(book, user):
    if not user.is_authenticated:
        return False
    return WishlistItem.objects.filter(user=user, book=book).exists()

@register.simple_tag
def wishlist_count(user):
    if not user.is_authenticated:
        return 0
    return WishlistItem.objects.filter(user=user).count()