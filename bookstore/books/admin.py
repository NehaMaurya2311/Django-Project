# books/admin.py - Updated with Sub-subcategory support
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from .models import Category, SubCategory, SubSubCategory, Author, Publisher, Book, Cart, CartItem

class SubSubCategoryInline(admin.TabularInline):
    """Inline for sub-subcategories within subcategory admin"""
    model = SubSubCategory
    extra = 0
    fields = ('name', 'slug', 'description', 'is_active', 'book_count_inline')
    readonly_fields = ('book_count_inline',)
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count_inline(self, obj):
        """Show book count for each sub-subcategory inline"""
        if obj.pk:
            count = Book.objects.filter(subsubcategory=obj).count()
            if count > 0:
                url = reverse('admin:books_book_changelist') + f'?subsubcategory__id__exact={obj.id}'
                return format_html('<a href="{}" target="_blank">{} books</a>', url, count)
            return '0 books'
        return '—'
    book_count_inline.short_description = 'Books'

class SubCategoryInline(admin.TabularInline):
    """Inline for subcategories within category admin"""
    model = SubCategory
    extra = 0
    fields = ('name', 'slug', 'description', 'is_active', 'book_count_inline', 'subsubcategory_count')
    readonly_fields = ('book_count_inline', 'subsubcategory_count')
    prepopulated_fields = {'slug': ('name',)}
    
    def book_count_inline(self, obj):
        """Show book count for each subcategory inline"""
        if obj.pk:
            count = Book.objects.filter(subcategory=obj).count()
            if count > 0:
                url = reverse('admin:books_book_changelist') + f'?subcategory__id__exact={obj.id}'
                return format_html('<a href="{}" target="_blank">{} books</a>', url, count)
            return '0 books'
        return '—'
    book_count_inline.short_description = 'Books'
    
    def subsubcategory_count(self, obj):
        """Show sub-subcategory count"""
        if obj.pk:
            count = obj.subsubcategories.count()
            if count > 0:
                url = reverse('admin:books_subsubcategory_changelist') + f'?subcategory__id__exact={obj.id}'
                return format_html('<a href="{}" target="_blank">{} sub-subcategories</a>', url, count)
            return '0 sub-subcategories'
        return '—'
    subsubcategory_count.short_description = 'Sub-subcategories'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name_with_icon', 'slug', 'subcategory_count', 'total_books', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display Settings', {
            'fields': ('image', 'is_active')
        }),
    )
    
    def name_with_icon(self, obj):
        """Display category name with appropriate icon"""
        icons = {
            'Fiction': '📚',
            'Non Fiction': '🧠', 
            'Coffee Table': '☕',
            'Hindi Novels': '🇮🇳',
            'Comics & Manga': '🦸',
            'Children Books': '👶'
        }
        icon = icons.get(obj.name, '📖')
        return format_html('<span style="font-size: 18px;">{}</span> <strong>{}</strong>', icon, obj.name)
    name_with_icon.short_description = 'Category'
    name_with_icon.admin_order_field = 'name'
    
    def subcategory_count(self, obj):
        """Display number of subcategories with link to filtered view"""
        count = obj.subcategories.count()
        if count > 0:
            url = reverse('admin:books_subcategory_changelist') + f'?category__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #007cba; font-weight: bold;">'
                '📁 {} subcategories</a>', 
                url, count
            )
        return format_html('<span style="color: #666;">0 subcategories</span>')
    subcategory_count.short_description = 'Subcategories'
    
    def total_books(self, obj):
        """Display total number of books in this category and all its subcategories"""
        direct_books = obj.books.count()
        subcategory_books = Book.objects.filter(subcategory__category=obj).count()
        subsubcategory_books = Book.objects.filter(subsubcategory__subcategory__category=obj).count()
        total = direct_books + subcategory_books + subsubcategory_books
        
        if total > 0:
            url = reverse('admin:books_book_changelist') + f'?category__id__exact={obj.id}'
            return format_html(
                '<a href="{}" style="color: #28a745; font-weight: bold;">'
                '📖 {} books</a>', 
                url, total
            )
        return format_html('<span style="color: #666;">0 books</span>')
    total_books.short_description = 'Total Books'

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name_with_category', 'slug', 'book_count', 'subsubcategory_count', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubSubCategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def name_with_category(self, obj):
        """Display subcategory name with its parent category"""
        category_icons = {
            'Fiction': '📚',
            'Non Fiction': '🧠', 
            'Coffee Table': '☕',
            'Hindi Novels': '🇮🇳',
            'Comics & Manga': '🦸',
            'Children Books': '👶'
        }
        icon = category_icons.get(obj.category.name, '📖')
        return format_html(
            '<span style="font-size: 12px;">{}</span> <strong>{}</strong>'
            '<br><small style="color: #007cba;">{}</small>',
            icon, obj.name, obj.category.name
        )
    name_with_category.short_description = 'Subcategory'
    name_with_category.admin_order_field = 'name'
    
    def book_count(self, obj):
        """Display number of books in this subcategory"""
        count = Book.objects.filter(subcategory=obj).count()
        if count > 0:
            url = reverse('admin:books_book_changelist') + f'?subcategory__id__exact={obj.id}'
            return format_html('<a href="{}">{} books</a>', url, count)
        return '0 books'
    book_count.short_description = 'Books'
    
    def subsubcategory_count(self, obj):
        """Show sub-subcategory count"""
        if obj.pk:
            count = obj.subsubcategories.count()
            if count > 0:
                url = reverse('admin:books_subsubcategory_changelist') + f'?subcategory__id__exact={obj.id}'
                return format_html('<a href="{}" target="_blank">{} sub-subcategories</a>', url, count)
            return '0 sub-subcategories'
        return '—'
    subsubcategory_count.short_description = 'Sub-subcategories'

@admin.register(SubSubCategory)
class SubSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name_with_hierarchy', 'slug', 'book_count', 'is_active']
    list_filter = ['is_active', 'subcategory__category', 'subcategory']
    search_fields = ['name', 'description', 'subcategory__name', 'subcategory__category__name']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('subcategory', 'name', 'slug', 'description')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def name_with_hierarchy(self, obj):
        """Display sub-subcategory name with full hierarchy"""
        category_icons = {
            'Fiction': '📚',
            'Non Fiction': '🧠', 
            'Coffee Table': '☕',
            'Hindi Novels': '🇮🇳',
            'Comics & Manga': '🦸',
            'Children Books': '👶'
        }
        icon = category_icons.get(obj.subcategory.category.name, '📖')
        return format_html(
            '<span style="font-size: 12px;">{}</span> <strong>{}</strong>'
            '<br><small style="color: #007cba;">{} > {}</small>',
            icon, obj.name, obj.subcategory.category.name, obj.subcategory.name
        )
    name_with_hierarchy.short_description = 'Sub-subcategory'
    name_with_hierarchy.admin_order_field = 'name'
    
    def book_count(self, obj):
        """Display number of books in this sub-subcategory"""
        count = Book.objects.filter(subsubcategory=obj).count()
        if count > 0:
            url = reverse('admin:books_book_changelist') + f'?subsubcategory__id__exact={obj.id}'
            return format_html('<a href="{}">{} books</a>', url, count)
        return '0 books'
    book_count.short_description = 'Books'

class BookAdminForm(forms.ModelForm):
    """Custom form for Book admin with hierarchical category dropdown"""
    
    class Meta:
        model = Book
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determine the initial category, subcategory, and sub-subcategory.
        # This covers both initial load of an existing object and form re-rendering after a validation error.
        instance_category = self.instance.category if self.instance else None
        instance_subcategory = self.instance.subcategory if self.instance else None
        
        # Override with form data if available (e.g., after a validation error)
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                instance_category = Category.objects.get(pk=category_id)
            except (ValueError, TypeError, Category.DoesNotExist):
                instance_category = None
        
        if 'subcategory' in self.data:
            try:
                subcategory_id = int(self.data.get('subcategory'))
                instance_subcategory = SubCategory.objects.get(pk=subcategory_id)
            except (ValueError, TypeError, SubCategory.DoesNotExist):
                instance_subcategory = None
        
        # Filter the subcategory queryset based on the determined category
        if instance_category:
            self.fields['subcategory'].queryset = SubCategory.objects.filter(
                category=instance_category,
                is_active=True
            ).order_by('name')
        else:
            self.fields['subcategory'].queryset = SubCategory.objects.none()
            
        # Filter the sub-subcategory queryset based on the determined subcategory
        if instance_subcategory:
            self.fields['subsubcategory'].queryset = SubSubCategory.objects.filter(
                subcategory=instance_subcategory,
                is_active=True
            ).order_by('name')
        else:
            self.fields['subsubcategory'].queryset = SubSubCategory.objects.none()
            
        # Set help text as the JS will handle the dynamic loading
        self.fields['subcategory'].help_text = 'Select a category first'
        self.fields['subsubcategory'].help_text = 'Select a subcategory first'


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'nationality', 'birth_date', 'book_count', 'has_image']
    search_fields = ['name', 'biography', 'nationality']
    list_filter = ['nationality', 'birth_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'biography')
        }),
        ('Personal Details', {
            'fields': ('birth_date', 'nationality', 'website'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('image',)
        }),
    )
    
    def book_count(self, obj):
        count = obj.books.count()
        if count > 0:
            url = reverse('admin:books_book_changelist') + f'?authors__id__exact={obj.id}'
            return format_html('<a href="{}">{} books</a>', url, count)
        return '0 books'
    book_count.short_description = 'Books'
    
    def has_image(self, obj):
        if obj.image:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    has_image.short_description = 'Image'
    has_image.boolean = True

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'established_year', 'book_count', 'has_website']
    search_fields = ['name', 'description']
    list_filter = ['established_year']
    
    def book_count(self, obj):
        count = Book.objects.filter(publisher=obj).count()
        if count > 0:
            url = reverse('admin:books_book_changelist') + f'?publisher__id__exact={obj.id}'
            return format_html('<a href="{}">{} books</a>', url, count)
        return '0 books'
    book_count.short_description = 'Books'
    
    def has_website(self, obj):
        if obj.website:
            return format_html('<a href="{}" target="_blank">Visit</a>', obj.website)
        return '—'
    has_website.short_description = 'Website'

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm
    list_display = [
        'title_with_cover', 'category_hierarchy_display', 'price', 'original_price', 
        'discount_percentage_display', 'warehouse_status_display', 'format', 'featured_badges', 'views_count'
    ]
    list_filter = [
        'status', 'format', 'is_featured', 'is_bestseller', 'is_on_sale', 
        'category', 'subcategory', 'subsubcategory', 'language', 'created_at'
    ]
    search_fields = [
        'title', 'isbn', 'isbn13', 'authors__name', 'publisher__name', 'google_books_id'
    ]
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['authors']
    readonly_fields = ['views_count', 'created_at', 'updated_at', 'google_books_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'authors', 'publisher', 'description', 'short_description')
        }),
        ('Classification', {
            'fields': ('category', 'subcategory', 'subsubcategory', 'format', 'language'),
            'description': 'Choose category first, then subcategory, then sub-subcategory if applicable'
        }),
        ('Identifiers', {
            'fields': ('isbn', 'isbn13', 'google_books_id'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('price', 'original_price')
        }),
        ('Physical Details', {
            'fields': ('pages', 'weight', 'dimensions', 'edition', 'publication_date'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('cover_image', 'cover_image_url', 'google_books_preview', 'additional_images')
        }),
        ('Status & Features', {
            'fields': ('status', 'is_featured', 'is_bestseller', 'is_on_sale')
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    class Media:
        js = ('admin/js/book_admin.js',)
    
    def title_with_cover(self, obj):
        cover_url = obj.get_cover_image_url
        if cover_url:
            return format_html(
                '<div style="display: flex; align-items: center;">'
                '<img src="{}" style="width: 40px; height: 60px; object-fit: cover; margin-right: 10px; border-radius: 3px;">'
                '<div><strong>{}</strong><br><small>by {}</small></div>'
                '</div>',
                cover_url,
                obj.title[:50] + ('...' if len(obj.title) > 50 else ''),
                ', '.join([author.name for author in obj.authors.all()[:2]])
            )
        return format_html('<strong>{}</strong><br><small>by {}</small>', 
                         obj.title[:50] + ('...' if len(obj.title) > 50 else ''),
                         ', '.join([author.name for author in obj.authors.all()[:2]]))
    title_with_cover.short_description = 'Book'
    title_with_cover.admin_order_field = 'title'
    
    def category_hierarchy_display(self, obj):
        """Show full Category > Subcategory > Sub-subcategory hierarchy"""
        category_icons = {
            'Fiction': '📚',
            'Non Fiction': '🧠', 
            'Coffee Table': '☕',
            'Hindi Novels': '🇮🇳',
            'Comics & Manga': '🦸',
            'Children Books': '👶'
        }
        icon = category_icons.get(obj.category.name, '📖')
        
        hierarchy_parts = [f'<span style="font-size: 12px;">{icon}</span> <strong>{obj.category.name}</strong>']
        
        if obj.subcategory:
            hierarchy_parts.append(f'<small style="color: #007cba;">› {obj.subcategory.name}</small>')
            
            if obj.subsubcategory:
                hierarchy_parts.append(f'<small style="color: #28a745;">› {obj.subsubcategory.name}</small>')
        else:
            hierarchy_parts.append('<small style="color: #666;">No subcategory</small>')
        
        return format_html('<br>'.join(hierarchy_parts))
    category_hierarchy_display.short_description = 'Category Hierarchy'
    category_hierarchy_display.admin_order_field = 'category__name'
    
    def discount_percentage_display(self, obj):
        discount = obj.discount_percentage
        if discount > 0:
            return format_html('<span style="color: green; font-weight: bold;">{}% OFF</span>', discount)
        return '—'
    discount_percentage_display.short_description = 'Discount'
    
    def featured_badges(self, obj):
        badges = []
        if obj.is_featured:
            badges.append('<span style="background: #007cba; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">FEATURED</span>')
        if obj.is_bestseller:
            badges.append('<span style="background: #ff6b35; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">BESTSELLER</span>')
        if obj.is_on_sale:
            badges.append('<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">ON SALE</span>')
        
        return format_html(' '.join(badges)) if badges else '—'
    featured_badges.short_description = 'Badges'
    
    def google_books_preview(self, obj):
        if obj.google_books_id:
            preview_url = f"https://books.google.com/books?id={obj.google_books_id}"
            return format_html(
                '<a href="{}" target="_blank">View on Google Books</a><br>'
                '<small>ID: {}</small>',
                preview_url, obj.google_books_id
            )
        return 'Not available'
    google_books_preview.short_description = 'Google Books'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'subcategory', 'subsubcategory', 'publisher'
        ).prefetch_related('authors')
    
    # Custom actions
    actions = ['mark_as_featured', 'mark_as_bestseller', 'mark_on_sale', 'mark_available', 'mark_out_of_stock']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} books marked as featured.')
    mark_as_featured.short_description = "Mark selected books as featured"
    
    def mark_as_bestseller(self, request, queryset):
        updated = queryset.update(is_bestseller=True)
        self.message_user(request, f'{updated} books marked as bestsellers.')
    mark_as_bestseller.short_description = "Mark selected books as bestsellers"
    
    def mark_on_sale(self, request, queryset):
        updated = queryset.update(is_on_sale=True)
        self.message_user(request, f'{updated} books marked as on sale.')
    mark_on_sale.short_description = "Mark selected books as on sale"
    
    def mark_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} books marked as available.')
    mark_available.short_description = "Mark selected books as available"
    
    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(status='out_of_stock')
        self.message_user(request, f'{updated} books marked as out of stock.')
    mark_out_of_stock.short_description = "Mark selected books as out of stock"

    def warehouse_status_display(self, obj):
        """Show actual warehouse stock status"""
        try:
            stock = obj.stock
            if stock.is_out_of_stock:
                return format_html('<span style="color: red; font-weight: bold;">OUT OF STOCK</span>')
            elif stock.needs_reorder:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">LOW STOCK ({})</span>', 
                    stock.available_quantity
                )
            else:
                return format_html(
                    '<span style="color: green; font-weight: bold;">IN STOCK ({})</span>', 
                    stock.available_quantity
                )
        except:
            return format_html('<span style="color: red;">NO STOCK RECORD</span>')
    
    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        # Add sale status to the list display
        if 'sale_status' not in list_display:
            list_display.insert(-1, 'sale_status')  # Insert before the last item
        return list_display
    
    def sale_status(self, obj):
        if obj.is_on_sale_now:
            return format_html(
                '<span style="color: red; font-weight: bold;">ON SALE ({}% OFF)</span>',
                obj.sale_discount_percentage
            )
        return format_html('<span style="color: gray;">No Sale</span>')
    sale_status.short_description = 'Sale Status'
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        readonly_fields.extend(['sale_status'])
        return readonly_fields


    warehouse_status_display.short_description = 'Warehouse Status'
    warehouse_status_display.admin_order_field = 'stock__quantity'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_items', 'total_price_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['total_items', 'total_price_display', 'created_at', 'updated_at']
    
    def total_price_display(self, obj):
        return f'₹{obj.total_price:.2f}'
    total_price_display.short_description = 'Total Price'
    total_price_display.admin_order_field = 'total_price'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart_user', 'book', 'quantity', 'unit_price', 'total_price_display']
    list_filter = ['created_at']
    search_fields = ['cart__user__username', 'book__title']
    readonly_fields = ['total_price_display', 'created_at']
    
    def cart_user(self, obj):
        return obj.cart.user.username
    cart_user.short_description = 'User'
    cart_user.admin_order_field = 'cart__user__username'
    
    def unit_price(self, obj):
        return f'₹{obj.book.price:.2f}'
    unit_price.short_description = 'Unit Price'
    
    def total_price_display(self, obj):
        return f'₹{obj.total_price:.2f}'
    total_price_display.short_description = 'Total Price'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cart__user', 'book')

# Customize admin site header and title
admin.site.site_header = "📚 BookStore Administration"
admin.site.site_title = "BookStore Admin"
admin.site.index_title = "Welcome to BookStore Administration"