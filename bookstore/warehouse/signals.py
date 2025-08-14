from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Stock, StockMovement

@receiver(post_save, sender=Stock)
def update_book_status_on_stock_change(sender, instance, **kwargs):
    """Update book status when stock changes"""
    instance.update_book_status()

@receiver(post_save, sender=StockMovement)
def update_book_status_on_movement(sender, instance, created, **kwargs):
    """Update book status when stock movement occurs"""
    if created:
        instance.stock.update_book_status()
