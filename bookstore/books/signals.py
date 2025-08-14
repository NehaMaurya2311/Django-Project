from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Book

@receiver(post_save, sender=Book)
def create_book_stock(sender, instance, created, **kwargs):
    """Automatically create Stock record when a new Book is created"""
    if created:
        from warehouse.models import Stock
        Stock.objects.get_or_create(
            book=instance,
            defaults={
                'quantity': 0,
                'reorder_level': 5,
                'max_stock_level': 100,
            }
        )