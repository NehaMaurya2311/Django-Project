# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def handle_user_post_save(sender, instance, created, **kwargs):
    """
    Handle user creation and updates
    Note: VendorProfile creation is now handled in the vendors app
    """
    # You can add any customer-specific logic here if needed
    pass