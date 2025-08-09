# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        # Set user_type to 'admin' for superusers
        if self.is_superuser:
            self.user_type = 'admin'
        # Set user_type to 'staff' for staff users if they're not admin
        elif self.is_staff and self.user_type not in ['admin']:
            self.user_type = 'staff'
        super().save(*args, **kwargs)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    preferences = models.JSONField(default=dict, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.user_type})"

    def get_full_address(self):
        return f"{self.address}, {self.city}, {self.state} - {self.pincode}"

    @classmethod
    def create_superuser(cls, username, email, password, **extra_fields):
        extra_fields['user_type'] = 'admin'
        return super().create_superuser(username, email, password, **extra_fields)
