# books/admin.py
from django.contrib import admin
from .models import Category, SubCategory, Author, Publisher, Book, Cart, CartItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'nationality', 'birth_date']
    search_fields = ['name']
    list_filter = ['nationality']

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'price', 'status', 'is_featured', 'is_bestseller', 'is_on_sale']
    list_filter = ['status', 'is_featured', 'is_bestseller', 'is_on_sale', 'category', 'format']
    search_fields = ['title', 'isbn', 'isbn13', 'authors__name']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['authors']

admin.site.register(SubCategory)
admin.site.register(Publisher)
admin.site.register(Cart)
admin.site.register(CartItem)
