# wishlist/models.py
from django.db import models
from django.contrib.auth import get_user_model
from books.models import Book

User = get_user_model()

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class WishlistCollection(models.Model):
    PRIVACY_CHOICES = (
        ('private', 'Private'),
        ('public', 'Public'),
        ('friends', 'Friends Only'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_collections')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='private')
    
    books = models.ManyToManyField(Book, through='WishlistCollectionItem')
    
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = ('user', 'name')
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"

class WishlistCollectionItem(models.Model):
    collection = models.ForeignKey(WishlistCollection, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, help_text="Personal notes about this book")
    priority = models.PositiveIntegerField(default=1, help_text="1=Low, 5=High")
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('collection', 'book')
        ordering = ['-priority', '-added_at']
    
    def __str__(self):
        return f"{self.collection.name} - {self.book.title}"

