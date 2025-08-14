# books/models.py - Updated with Sub-subcategory support
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('books:category_books', kwargs={'slug': self.slug})

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Sub Categories"
        unique_together = ('category', 'slug')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_absolute_url(self):
        return reverse('books:subcategory_books', kwargs={
            'category_slug': self.category.slug,
            'subcategory_slug': self.slug
        })

class SubSubCategory(models.Model):
    """Third level category hierarchy"""
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='subsubcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Sub-Sub Categories"
        unique_together = ('subcategory', 'slug')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.subcategory.category.name} - {self.subcategory.name} - {self.name}"
    
    @property
    def category(self):
        return self.subcategory.category
    
    def get_absolute_url(self):
        return reverse('books:subsubcategory_books', kwargs={
            'category_slug': self.subcategory.category.slug,
            'subcategory_slug': self.subcategory.slug,
            'subsubcategory_slug': self.slug
        })

class Author(models.Model):
    name = models.CharField(max_length=200)
    biography = models.TextField(blank=True)
    image = models.ImageField(upload_to='authors/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    
    def __str__(self):
        return self.name

class Publisher(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    established_year = models.PositiveIntegerField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Book(models.Model):
    BOOK_FORMATS = (
        ('hardcover', 'Hardcover'),
        ('paperback', 'Paperback'),
        ('ebook', 'E-book'),
        ('audiobook', 'Audiobook'),
    )
    
    BOOK_STATUS = (
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    )
    
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True)
    isbn = models.CharField(max_length=20, unique=True, blank=True)
    isbn13 = models.CharField(max_length=20, unique=True, blank=True)
    
    # Updated category hierarchy
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='books')
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    subsubcategory = models.ForeignKey(SubSubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    format = models.CharField(max_length=20, choices=BOOK_FORMATS, default='paperback')
    pages = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=50, default='English')
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Updated to handle both file uploads and URLs
    cover_image = models.ImageField(upload_to='books/covers/', blank=True, null=True)
    cover_image_url = models.URLField(max_length=1000, blank=True, null=True, help_text="External cover image URL (e.g., from Google Books)")
    additional_images = models.JSONField(default=list, blank=True)
    
    publication_date = models.DateField(blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True)
    
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, help_text="Weight in grams")
    dimensions = models.CharField(max_length=100, blank=True, help_text="Format: Length x Width x Height")
    
    status = models.CharField(max_length=20, choices=BOOK_STATUS, default='available')
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_on_sale = models.BooleanField(default=False)
    
    google_books_id = models.CharField(max_length=50, blank=True, unique=True, null=True, help_text="Google Books API ID")
    
    views_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['subcategory', 'status']),
            models.Index(fields=['subsubcategory', 'status']),
            models.Index(fields=['is_bestseller', 'status']),
            models.Index(fields=['is_on_sale', 'status']),
            models.Index(fields=['google_books_id']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('books:book_detail', kwargs={'slug': self.slug})
    
    def clean(self):
        """Validate category hierarchy"""
        from django.core.exceptions import ValidationError
        
        # If subcategory is selected, it must belong to the selected category
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError({
                'subcategory': f'Selected subcategory does not belong to category "{self.category.name}"'
            })
        
        # If subsubcategory is selected, it must belong to the selected subcategory
        if self.subsubcategory:
            if not self.subcategory:
                raise ValidationError({
                    'subsubcategory': 'You must select a subcategory before selecting a sub-subcategory'
                })
            if self.subsubcategory.subcategory != self.subcategory:
                raise ValidationError({
                    'subsubcategory': f'Selected sub-subcategory does not belong to subcategory "{self.subcategory.name}"'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def get_cover_image_url(self):
        """Get the cover image URL, prioritizing uploaded files over external URLs"""
        if self.cover_image:
            return self.cover_image.url
        elif self.cover_image_url:
            return self.cover_image_url
        return None
    
    @property
    def category_hierarchy(self):
        """Get the full category hierarchy as a string"""
        hierarchy = [self.category.name]
        if self.subcategory:
            hierarchy.append(self.subcategory.name)
        if self.subsubcategory:
            hierarchy.append(self.subsubcategory.name)
        return " > ".join(hierarchy)
    
    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    @property
    def average_rating(self):
        from reviews.models import Review
        reviews = Review.objects.filter(book=self, status='approved')
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0
    
    @property
    def total_reviews(self):
        from reviews.models import Review
        return Review.objects.filter(book=self, status='approved').count()
    
    def increment_view_count(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])

    @property
    def current_stock_level(self):
        """Get current stock level from warehouse"""
        try:
            return self.stock.available_quantity
        except:
            return 0
    
    @property
    def is_in_stock(self):
        """Check if book is actually in stock in warehouse"""
        try:
            return self.stock.available_quantity > 0
        except:
            return False
    
    @property
    def stock_status_display(self):
        """Get readable stock status"""
        try:
            stock = self.stock
            if stock.is_out_of_stock:
                return "Out of Stock"
            elif stock.needs_reorder:
                return f"Low Stock ({stock.available_quantity} left)"
            else:
                return f"In Stock ({stock.available_quantity} available)"
        except:
            return "No Stock Record"



class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart of {self.user.username}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('cart', 'book')
    
    def __str__(self):
        return f"{self.quantity} x {self.book.title}"
    
    @property
    def total_price(self):
        return self.book.price * self.quantity