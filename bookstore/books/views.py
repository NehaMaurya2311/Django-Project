# books/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
from django.urls import reverse
from django.conf import settings
from django.db import IntegrityError
from django.views.decorators.http import require_http_methods
import json
import requests
from .models import Book, Category, Cart, CartItem, Author, Publisher, SubCategory, SubSubCategory
from .forms import BookForm, BookFilterForm
from warehouse.models import Stock
from django.contrib.admin.views.decorators import staff_member_required
from coupons.models import BookSale, BookSaleItem


@staff_member_required
def load_subcategories(request):
    """AJAX view to load subcategories based on selected category"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({
            'subcategories': [],
            'category_name': '',
            'error': 'No category ID provided'
        })
    
    try:
        category = get_object_or_404(Category, id=category_id)
        subcategories = list(category.subcategories.filter(is_active=True).values('id', 'name'))
        
        return JsonResponse({
            'subcategories': subcategories,
            'category_name': category.name,
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'subcategories': [],
            'category_name': '',
            'error': str(e)
        })

@staff_member_required
def load_subsubcategories(request):
    """AJAX view to load sub-subcategories based on selected subcategory"""
    subcategory_id = request.GET.get('subcategory_id')
    
    if not subcategory_id:
        return JsonResponse({
            'subsubcategories': [],
            'subcategory_name': '',
            'error': 'No subcategory ID provided'
        })
    
    try:
        subcategory = get_object_or_404(Subcategory, id=subcategory_id)
        subsubcategories = list(subcategory.subsubcategories.filter(is_active=True).values('id', 'name'))
        
        return JsonResponse({
            'subsubcategories': subsubcategories,
            'subcategory_name': subcategory.name,
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'subsubcategories': [],
            'subcategory_name': '',
            'error': str(e)
        })

def home(request):
    """Updated home view with sales-aware book displays"""
    
    # Get featured books with sale information
    featured_books_qs = Book.objects.filter(is_featured=True, status='available').select_related('category')
    featured_books = []
    for book in featured_books_qs[:8]:
        featured_books.append({
            'book': book,
            'is_on_sale': book.is_on_sale_now,
            'original_price': book.price,
            'sale_price': book.sale_price,
            'discount_percentage': book.sale_discount_percentage,
            'has_coupons': book.has_available_coupons
        })
    
    # Get bestseller books with sale information
    bestseller_books_qs = Book.objects.filter(is_bestseller=True, status='available').select_related('category')
    bestseller_books = []
    for book in bestseller_books_qs[:8]:
        bestseller_books.append({
            'book': book,
            'is_on_sale': book.is_on_sale_now,
            'original_price': book.price,
            'sale_price': book.sale_price,
            'discount_percentage': book.sale_discount_percentage,
            'has_coupons': book.has_available_coupons
        })
    
    # Get books that are currently on sale (for the sale section)
    from django.utils import timezone
    from coupons.models import BookSaleItem
    
    current_time = timezone.now()
    
    # Debug: Check if there are any active sales
    active_sales = BookSale.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_to__gte=current_time
    )
    print(f"Active sales: {active_sales.count()}")
    
    sale_items = BookSaleItem.objects.select_related('book', 'sale').filter(
        sale__is_active=True,
        sale__valid_from__lte=current_time,
        sale__valid_to__gte=current_time,
        book__status='available'
    )[:8]
    
    print(f"Sale items found: {sale_items.count()}")
    
    sale_books = []
    for sale_item in sale_items:
        sale_books.append({
            'book': sale_item.book,
            'is_on_sale': True,
            'original_price': sale_item.book.price,
            'sale_price': sale_item.get_sale_price(),
            'discount_percentage': sale_item.get_discount_percentage(),
            'has_coupons': sale_item.book.has_available_coupons,
            'sale_name': sale_item.sale.name
        })
    
    # Get categories
    categories = Category.objects.filter(is_active=True).annotate(
        book_count=Count('books', filter=Q(books__status='available'))
    )[:8]
    
    context = {
        'featured_books': featured_books,
        'bestseller_books': bestseller_books,
        'sale_books': sale_books,
        'categories': categories,
    }
    return render(request, 'books/home.html', context)

def map_google_books_category(google_category):
    """
    Map Google Books category to our THREE-LEVEL category structure
    Returns tuple: (main_category, subcategory, subsubcategory)
    """
    if not google_category:
        return 'Fiction', 'General Fiction', 'Contemporary Fiction'  # Default
    
    # Normalize the category name
    normalized = google_category.strip()
    lower_category = normalized.lower()
    
    # Fiction mappings
    if any(word in lower_category for word in ['fiction', 'novel']):
        if any(word in lower_category for word in ['young', 'teen', 'ya', 'juvenile']):
            return 'Fiction', 'Young Adult Fiction', 'YA Contemporary'
        elif any(word in lower_category for word in ['romance', 'love']):
            return 'Fiction', 'Romance', 'Contemporary Romance'
        elif any(word in lower_category for word in ['mystery', 'crime', 'thriller', 'detective']):
            return 'Fiction', 'Mystery & Thriller', 'Crime Fiction'
        elif any(word in lower_category for word in ['fantasy', 'magic']):
            return 'Fiction', 'Fantasy', 'Epic Fantasy'
        elif any(word in lower_category for word in ['science', 'sci-fi', 'scifi']):
            return 'Fiction', 'Science Fiction', 'Space Opera'
        elif any(word in lower_category for word in ['horror', 'scary']):
            return 'Fiction', 'Horror', 'Psychological Horror'
        elif any(word in lower_category for word in ['historical']):
            return 'Fiction', 'Historical Fiction', 'Historical Drama'
        elif any(word in lower_category for word in ['adventure']):
            return 'Fiction', 'Adventure', 'Action & Adventure'
        elif any(word in lower_category for word in ['classic']):
            return 'Fiction', 'Classics', 'Literary Classics'
        elif any(word in lower_category for word in ['women', 'womens']):
            return 'Fiction', 'Women\'s Fiction', 'Contemporary Women\'s Fiction'
        else:
            return 'Fiction', 'General Fiction', 'Contemporary Fiction'
    
    # Non-Fiction mappings
    elif any(word in lower_category for word in ['biography', 'memoir', 'autobiography']):
        return 'Non Fiction', 'Biography & Memoir', 'Celebrity Biographies'
    elif any(word in lower_category for word in ['business', 'management', 'economics']):
        return 'Non Fiction', 'Business & Economics', 'Management & Leadership'
    elif any(word in lower_category for word in ['health', 'fitness', 'diet', 'wellness']):
        return 'Non Fiction', 'Health & Wellness', 'Diet & Nutrition'
    elif any(word in lower_category for word in ['self', 'help', 'motivation', 'psychology']):
        return 'Non Fiction', 'Self-Help & Personal Development', 'Motivational'
    elif any(word in lower_category for word in ['history', 'historical']):
        return 'Non Fiction', 'History', 'World History'
    elif any(word in lower_category for word in ['travel', 'tourism', 'holiday']):
        return 'Non Fiction', 'Travel', 'Travel Guides'
    elif any(word in lower_category for word in ['science', 'nature', 'physics', 'chemistry', 'biology']):
        return 'Non Fiction', 'Science & Nature', 'Popular Science'
    elif any(word in lower_category for word in ['philosophy', 'philosophical']):
        return 'Non Fiction', 'Philosophy', 'Western Philosophy'
    elif any(word in lower_category for word in ['spiritual', 'religion', 'religious']):
        return 'Non Fiction', 'Religion & Spirituality', 'Spiritual Growth'
    elif any(word in lower_category for word in ['reference', 'dictionary', 'encyclopedia']):
        return 'Non Fiction', 'Reference', 'Dictionaries'
    elif any(word in lower_category for word in ['sports', 'sport', 'games']):
        return 'Non Fiction', 'Sports & Recreation', 'General Sports'
    
    # Children's books
    elif any(word in lower_category for word in ['children', 'kids', 'juvenile']):
        if any(word in lower_category for word in ['0', '1', '2', '3', '4', '5']):
            return 'Children Books', 'Early Childhood (0-5)', 'Picture Books'
        elif any(word in lower_category for word in ['6', '7', '8']):
            return 'Children Books', 'Elementary (5-8)', 'Beginning Readers'
        else:
            return 'Children Books', 'Middle Grade (8-13)', 'Chapter Books'
    
    # Comics & Manga
    elif any(word in lower_category for word in ['comics', 'comic']):
        return 'Comics & Manga', 'Comics', 'Superhero Comics'
    elif 'manga' in lower_category:
        return 'Comics & Manga', 'Manga', 'Shonen Manga'
    elif any(word in lower_category for word in ['graphic', 'novel']):
        return 'Comics & Manga', 'Graphic Novels', 'Contemporary Graphic Novels'
    
    # Coffee Table (visual/art books)
    elif any(word in lower_category for word in ['art', 'painting', 'music', 'photography']):
        return 'Coffee Table', 'Art & Photography', 'Fine Art'
    elif any(word in lower_category for word in ['cooking', 'food', 'recipe']):
        return 'Coffee Table', 'Food & Cooking', 'International Cuisine'
    elif any(word in lower_category for word in ['design', 'interior', 'architecture']):
        return 'Coffee Table', 'Design & Architecture', 'Interior Design'
    elif any(word in lower_category for word in ['car', 'auto', 'vehicle']):
        return 'Coffee Table', 'Transportation', 'Classic Cars'
    elif any(word in lower_category for word in ['wildlife', 'animal']):
        return 'Coffee Table', 'Nature & Wildlife', 'Wildlife Photography'
    elif any(word in lower_category for word in ['garden', 'plant']):
        return 'Coffee Table', 'Gardening & Landscaping', 'Garden Design'
    elif any(word in lower_category for word in ['film', 'movie', 'cinema']):
        return 'Coffee Table', 'Entertainment', 'Cinema & Film'
    elif any(word in lower_category for word in ['lifestyle', 'fashion']):
        return 'Coffee Table', 'Lifestyle & Fashion', 'Fashion Photography'
    
    # Hindi/Indian language books
    elif any(word in lower_category for word in ['hindi', 'indian', 'language']):
        return 'Hindi Novels', 'Contemporary Hindi Literature', 'Modern Hindi Fiction'
    
    # Default fallback
    else:
        return 'Fiction', 'General Fiction', 'Contemporary Fiction'

def get_or_create_category_hierarchy(category_name, subcategory_name, subsubcategory_name=None):
    """
    Get or create complete category hierarchy
    """
    # Get or create main category
    category, created = Category.objects.get_or_create(
        name=category_name,
        defaults={
            'slug': slugify(category_name),
            'description': f'{category_name} books collection',
            'is_active': True
        }
    )
    
    # Get or create subcategory
    subcategory = None
    if subcategory_name:
        subcategory, sub_created = SubCategory.objects.get_or_create(
            category=category,
            name=subcategory_name,
            defaults={
                'slug': slugify(subcategory_name),
                'description': f'{subcategory_name} in {category_name}',
                'is_active': True
            }
        )
    
    # Get or create sub-subcategory
    subsubcategory = None
    if subsubcategory_name and subcategory:
        subsubcategory, subsub_created = SubSubCategory.objects.get_or_create(
            subcategory=subcategory,
            name=subsubcategory_name,
            defaults={
                'slug': slugify(subsubcategory_name),
                'description': f'{subsubcategory_name} in {subcategory_name}',
                'is_active': True
            }
        )
    
    return category, subcategory, subsubcategory

@require_http_methods(["GET"])
def check_book_exists(request):
    """AJAX endpoint to check if a book already exists in the library"""
    google_books_id = request.GET.get('google_books_id')
    title = request.GET.get('title')
    author = request.GET.get('author')
    
    if not google_books_id and not (title and author):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
    existing_book = None
    
    # First check by Google Books ID
    if google_books_id:
        existing_book = Book.objects.filter(google_books_id=google_books_id).first()
    
    # If not found by Google Books ID, check by title and author
    if not existing_book and title and author:
        first_author = author.split(',')[0].strip()
        existing_book = Book.objects.filter(
            title__iexact=title.strip(),
            authors__name__iexact=first_author
        ).first()
    
    if existing_book:
        return JsonResponse({
            'exists': True,
            'book_id': existing_book.pk,
            'book_title': existing_book.title,
            'book_url': existing_book.get_absolute_url(),
            'book_slug': existing_book.slug
        })
    
    return JsonResponse({'exists': False})

def create_authors_from_string(authors_string):
    """Helper function to create authors from comma-separated string"""
    if not authors_string:
        return []
    
    authors = []
    author_names = [name.strip() for name in authors_string.split(',') if name.strip()]
    
    for author_name in author_names:
        author, created = Author.objects.get_or_create(
            name=author_name
        )
        authors.append(author)
    
    return authors

def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug, status='available')
    book.increment_view_count()
    
    related_books = Book.objects.filter(
        category=book.category, 
        status='available'
    ).exclude(id=book.id)[:4]
    
    # Check if in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        try:
            from wishlist.models import WishlistItem
            in_wishlist = WishlistItem.objects.filter(user=request.user, book=book).exists()
        except:
            pass
    
    context = {
        'book': book,
        'related_books': related_books,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'books/book_detail.html', context)

def category_books(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    books_list = Book.objects.filter(category=category, status='available').order_by('-created_at')
    
    # Filters
    price_filter = request.GET.get('price')
    format_filter = request.GET.get('format')
    author_filter = request.GET.get('author')
    subcategory_filter = request.GET.get('subcategory')
    subsubcategory_filter = request.GET.get('subsubcategory')
    
    if price_filter:
        if price_filter == 'low':
            books_list = books_list.filter(price__lt=500)
        elif price_filter == 'medium':
            books_list = books_list.filter(price__gte=500, price__lt=1000)
        elif price_filter == 'high':
            books_list = books_list.filter(price__gte=1000)
    
    if format_filter:
        books_list = books_list.filter(format=format_filter)
    
    if author_filter:
        books_list = books_list.filter(authors__id=author_filter)
    
    if subcategory_filter:
        books_list = books_list.filter(subcategory__slug=subcategory_filter)
    
    if subsubcategory_filter:
        books_list = books_list.filter(subsubcategory__slug=subsubcategory_filter)
    
    paginator = Paginator(books_list, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    # Get available filters
    authors = Author.objects.filter(books__category=category).distinct()
    subcategories = SubCategory.objects.filter(category=category, is_active=True)
    subsubcategories = SubSubCategory.objects.filter(subcategory__category=category, is_active=True)
    
    context = {
        'category': category,
        'books': books,
        'authors': authors,
        'subcategories': subcategories,
        'subsubcategories': subsubcategories,
    }
    return render(request, 'books/category_books.html', context)

def subcategory_books(request, category_slug, subcategory_slug):
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    subcategory = get_object_or_404(SubCategory, slug=subcategory_slug, category=category, is_active=True)
    books_list = Book.objects.filter(subcategory=subcategory, status='available').order_by('-created_at')
    
    # Apply filters
    price_filter = request.GET.get('price')
    format_filter = request.GET.get('format')
    author_filter = request.GET.get('author')
    subsubcategory_filter = request.GET.get('subsubcategory')
    
    if price_filter:
        if price_filter == 'low':
            books_list = books_list.filter(price__lt=500)
        elif price_filter == 'medium':
            books_list = books_list.filter(price__gte=500, price__lt=1000)
        elif price_filter == 'high':
            books_list = books_list.filter(price__gte=1000)
    
    if format_filter:
        books_list = books_list.filter(format=format_filter)
    
    if author_filter:
        books_list = books_list.filter(authors__id=author_filter)
    
    if subsubcategory_filter:
        books_list = books_list.filter(subsubcategory__slug=subsubcategory_filter)
    
    paginator = Paginator(books_list, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    authors = Author.objects.filter(books__subcategory=subcategory).distinct()
    subsubcategories = SubSubCategory.objects.filter(subcategory=subcategory, is_active=True)
    
    context = {
        'category': category,
        'subcategory': subcategory,
        'books': books,
        'authors': authors,
        'subsubcategories': subsubcategories,
    }
    return render(request, 'books/subcategory_books.html', context)

def subsubcategory_books(request, category_slug, subcategory_slug, subsubcategory_slug):
    """New view for sub-subcategory books"""
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    subcategory = get_object_or_404(SubCategory, slug=subcategory_slug, category=category, is_active=True)
    subsubcategory = get_object_or_404(SubSubCategory, slug=subsubcategory_slug, subcategory=subcategory, is_active=True)
    
    books_list = Book.objects.filter(subsubcategory=subsubcategory, status='available').order_by('-created_at')
    
    # Apply filters
    price_filter = request.GET.get('price')
    format_filter = request.GET.get('format')
    author_filter = request.GET.get('author')
    
    if price_filter:
        if price_filter == 'low':
            books_list = books_list.filter(price__lt=500)
        elif price_filter == 'medium':
            books_list = books_list.filter(price__gte=500, price__lt=1000)
        elif price_filter == 'high':
            books_list = books_list.filter(price__gte=1000)
    
    if format_filter:
        books_list = books_list.filter(format=format_filter)
    
    if author_filter:
        books_list = books_list.filter(authors__id=author_filter)
    
    paginator = Paginator(books_list, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    authors = Author.objects.filter(books__subsubcategory=subsubcategory).distinct()
    
    context = {
        'category': category,
        'subcategory': subcategory,
        'subsubcategory': subsubcategory,
        'books': books,
        'authors': authors,
    }
    return render(request, 'books/subsubcategory_books.html', context)

def all_books(request):
    books_list = Book.objects.filter(status='available').order_by('-created_at')
    
    # Apply filters
    price_filter = request.GET.get('price')
    format_filter = request.GET.get('format')
    author_filter = request.GET.get('author')
    category_filter = request.GET.get('category')
    subcategory_filter = request.GET.get('subcategory')
    subsubcategory_filter = request.GET.get('subsubcategory')
    
    if price_filter:
        if price_filter == 'low':
            books_list = books_list.filter(price__lt=500)
        elif price_filter == 'medium':
            books_list = books_list.filter(price__gte=500, price__lt=1000)
        elif price_filter == 'high':
            books_list = books_list.filter(price__gte=1000)
    
    if format_filter:
        books_list = books_list.filter(format=format_filter)
    
    if author_filter:
        books_list = books_list.filter(authors__id=author_filter)
    
    if category_filter:
        books_list = books_list.filter(category__slug=category_filter)
    
    if subcategory_filter:
        books_list = books_list.filter(subcategory__slug=subcategory_filter)
    
    if subsubcategory_filter:
        books_list = books_list.filter(subsubcategory__slug=subsubcategory_filter)
    
    paginator = Paginator(books_list, 24)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    # Get all filters data
    categories = Category.objects.filter(is_active=True)
    subcategories = SubCategory.objects.filter(is_active=True)
    subsubcategories = SubSubCategory.objects.filter(is_active=True)
    authors = Author.objects.filter(books__isnull=False).distinct()
    
    context = {
        'books': books,
        'categories': categories,
        'subcategories': subcategories,
        'subsubcategories': subsubcategories,
        'authors': authors,
    }
    return render(request, 'books/all_books.html', context)

def search_books(request):
    query = request.GET.get('q', '')
    source = request.GET.get('source', '')
    books_list = Book.objects.filter(status='available')
    
    if query:
        books_list = books_list.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(description__icontains=query) |
            Q(isbn__icontains=query) |
            Q(isbn13__icontains=query) |
            Q(google_books_id__icontains=query)
        ).distinct()
        
        # If searching from Google Books addition, prioritize exact matches
        if source == 'google_books':
            exact_title_matches = books_list.filter(title__iexact=query)
            if exact_title_matches.exists():
                books_list = exact_title_matches
            else:
                exact_author_matches = books_list.filter(authors__name__iexact=query)
                if exact_author_matches.exists():
                    books_list = exact_author_matches
        
        # Order by relevance
        books_list = books_list.annotate(
            title_exact_match=Count('id', filter=Q(title__iexact=query)),
            author_exact_match=Count('id', filter=Q(authors__name__iexact=query))
        ).order_by('-title_exact_match', '-author_exact_match', '-created_at')
    
    paginator = Paginator(books_list, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    context = {
        'books': books,
        'query': query,
        'source': source,
        'total_results': books_list.count(),
    }
    return render(request, 'books/search_results.html', context)

@login_required
def add_book(request):
    if request.method == 'POST':
        google_books_id = request.POST.get('google_books_id')
        
        if google_books_id:
            # Check for duplicates
            try:
                existing_book = Book.objects.filter(google_books_id=google_books_id).first()
                if existing_book:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'error': 'Book already exists in library',
                            'existing_book_url': existing_book.get_absolute_url(),
                            'existing_book_title': existing_book.title
                        }, status=400)
                    messages.warning(request, f'Book "{existing_book.title}" already exists in the library!')
                    return redirect('books:book_detail', slug=existing_book.slug)
                
                # Also check by title + first author
                title = request.POST.get('title', '').strip()
                authors_string = request.POST.get('authors', '').strip()
                
                if title and authors_string:
                    first_author = authors_string.split(',')[0].strip()
                    title_author_duplicate = Book.objects.filter(
                        title__iexact=title,
                        authors__name__iexact=first_author
                    ).first()
                    
                    if title_author_duplicate:
                        if not title_author_duplicate.google_books_id:
                            title_author_duplicate.google_books_id = google_books_id
                            title_author_duplicate.save()
                        
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': False, 
                                'error': 'Book with same title and author already exists',
                                'existing_book_url': title_author_duplicate.get_absolute_url(),
                                'existing_book_title': title_author_duplicate.title
                            }, status=400)
                        messages.warning(request, f'Book "{title_author_duplicate.title}" already exists in the library!')
                        return redirect('books:book_detail', slug=title_author_duplicate.slug)

            except Exception as e:
                print(f"Error checking for duplicates: {e}")
            
            # Create book from API data
            try:
                api_url = f"https://www.googleapis.com/books/v1/volumes/{google_books_id}?key={settings.GOOGLE_BOOKS_API_KEY}"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    api_data = response.json()
                    volume_info = api_data.get('volumeInfo', {})
                    
                    # Use API data as primary source
                    title = volume_info.get('title', request.POST.get('title', '')).strip()
                    description = volume_info.get('description', request.POST.get('description', ''))
                    authors_list = volume_info.get('authors', [])
                    categories_list = volume_info.get('categories', [])
                    
                    if not title:
                        raise ValueError("Book title is required")
                    
                    # Get cover image
                    image_links = volume_info.get('imageLinks', {})
                    cover_image_url = (
                        image_links.get('extraLarge') or
                        image_links.get('large') or
                        image_links.get('medium') or
                        image_links.get('thumbnail') or
                        request.POST.get('cover_image')
                    )
                    
                    # Get metadata
                    isbn_10 = None
                    isbn_13 = None
                    for identifier in volume_info.get('industryIdentifiers', []):
                        if identifier.get('type') == 'ISBN_10':
                            isbn_10 = identifier.get('identifier')
                        elif identifier.get('type') == 'ISBN_13':
                            isbn_13 = identifier.get('identifier')
                    
                    pages = volume_info.get('pageCount')
                    publisher_name = volume_info.get('publisher')
                    publication_date = volume_info.get('publishedDate')
                    language = volume_info.get('language', 'en')
                    
                    # Create unique slug
                    base_slug = slugify(title)
                    slug = base_slug
                    counter = 1
                    while Book.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    # Get or create publisher
                    publisher = None
                    if publisher_name:
                        publisher, created = Publisher.objects.get_or_create(
                            name=publisher_name
                        )
                    
                    # Handle categories with THREE-LEVEL mapping
                    if isinstance(categories_list, list) and categories_list:
                        primary_category = categories_list[0] if categories_list else ''
                    else:
                        primary_category = str(categories_list) if categories_list else ''
                    
                    # Map to our THREE-LEVEL category structure
                    main_category_name, subcategory_name, subsubcategory_name = map_google_books_category(primary_category)
                    
                    # Get or create the complete hierarchy
                    category, subcategory, subsubcategory = get_or_create_category_hierarchy(
                        main_category_name, subcategory_name, subsubcategory_name
                    )
                    
                    # Create the book
                    book = Book(
                        title=title,
                        description=description or "No description available",
                        google_books_id=google_books_id,
                        price=request.POST.get('price', 299.00),
                        slug=slug,
                        isbn=isbn_10,
                        isbn13=isbn_13,
                        pages=pages,
                        language=language,
                        publisher=publisher,
                        category=category,
                        subcategory=subcategory,
                        subsubcategory=subsubcategory  # NEW: Set sub-subcategory
                    )
                    
                    # Handle publication date
                    if publication_date:
                        try:
                            from datetime import datetime
                            if len(publication_date) == 4:  # Year only
                                book.publication_date = datetime.strptime(f"{publication_date}-01-01", "%Y-%m-%d").date()
                            elif len(publication_date) == 7:  # Year-Month
                                book.publication_date = datetime.strptime(f"{publication_date}-01", "%Y-%m-%d").date()
                            else:  # Full date
                                book.publication_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
                        except:
                            pass
                    
                    # Handle cover image URL
                    if cover_image_url and cover_image_url.startswith('http'):
                        if cover_image_url.startswith('http://'):
                            cover_image_url = cover_image_url.replace('http://', 'https://')
                        book.cover_image_url = cover_image_url
                
                else:
                    # Fallback to form data
                    title = request.POST.get('title', '').strip()
                    if not title:
                        raise ValueError("Book title is required")
                    
                    description = request.POST.get('description', 'No description available')
                    authors_list = request.POST.get('authors', '').split(',')
                    categories_list = request.POST.get('categories', '').split(',')
                    cover_image_url = request.POST.get('cover_image')
                    
                    slug = slugify(title)
                    counter = 1
                    base_slug = slug
                    while Book.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    # Handle categories for fallback
                    primary_category = categories_list[0] if categories_list else ''
                    main_category_name, subcategory_name, subsubcategory_name = map_google_books_category(primary_category)
                    category, subcategory, subsubcategory = get_or_create_category_hierarchy(
                        main_category_name, subcategory_name, subsubcategory_name
                    )
                    
                    book = Book(
                        title=title,
                        description=description,
                        google_books_id=google_books_id,
                        price=request.POST.get('price', 299.00),
                        slug=slug,
                        category=category,
                        subcategory=subcategory,
                        subsubcategory=subsubcategory
                    )
                    
                    if cover_image_url:
                        if cover_image_url.startswith('http://'):
                            cover_image_url = cover_image_url.replace('http://', 'https://')
                        book.cover_image_url = cover_image_url
                
                # Save the book
                try:
                    book.save()
                except IntegrityError as e:
                    error_msg = "Book already exists"
                    if 'google_books_id' in str(e):
                        error_msg = "Book with this Google Books ID already exists"
                    elif 'slug' in str(e):
                        error_msg = "Book with similar title already exists"
                    elif 'isbn' in str(e):
                        error_msg = "Book with this ISBN already exists"
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_msg}, status=400)
                    messages.error(request, error_msg)
                    return redirect('books:search_google_books')
                
                # Handle authors
                if isinstance(authors_list, list):
                    authors_string = ', '.join([str(author).strip() for author in authors_list if str(author).strip()])
                else:
                    authors_string = str(authors_list)
                
                authors = create_authors_from_string(authors_string)
                if authors:
                    book.authors.set(authors)
                
                # Return response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True, 
                        'book_id': book.pk,
                        'book_slug': book.slug,
                        'book_title': book.title,
                        'redirect_url': reverse('books:book_detail', kwargs={'slug': book.slug})
                    })
                    
                messages.success(request, f'Book "{book.title}" added successfully!')
                return redirect('books:book_detail', slug=book.slug)
                
            except requests.exceptions.RequestException:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Network error while fetching book details'}, status=400)
                messages.error(request, 'Network error while adding book. Please try again.')
            except ValueError as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                messages.error(request, str(e))
            except Exception as e:
                print(f"Unexpected error adding book: {e}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': f'Error adding book: {str(e)}'}, status=400)
                messages.error(request, f'Error adding book: {str(e)}')
                
            return redirect('books:search_google_books')
        
        # Handle regular form submission (manual entry)
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Book "{book.title}" added successfully!')
            return redirect('books:book_detail', slug=book.slug)
    else:
        form = BookForm()
    
    return render(request, 'books/add_book.html', {'form': form})

@login_required
def delete_book(request, slug):
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete books.')
        return redirect('books:home')
    
    book = get_object_or_404(Book, slug=slug)
    
    if request.method == 'POST':
        book_title = book.title
        book.delete()
        messages.success(request, f'Book "{book_title}" has been deleted.')
        return redirect('books:all_books')
    
    return render(request, 'books/delete_book.html', {'book': book})

@login_required
def search_google_books(request):
    if request.method == 'GET':
        query = request.GET.get('q')
        search_type = request.GET.get('search_type', 'title')
        books = []
        
        if query:
            try:
                all_books = []
                max_results_per_page = 40
                max_pages = 3
                
                for page in range(max_pages):
                    start_index = page * max_results_per_page
                    
                    if search_type == 'author':
                        search_query = f"inauthor:{query}"
                    else:
                        search_query = query
                    
                    url = (
                        f"https://www.googleapis.com/books/v1/volumes?"
                        f"q={search_query}&"
                        f"maxResults={max_results_per_page}&"
                        f"startIndex={start_index}&"
                        f"key={settings.GOOGLE_BOOKS_API_KEY}"
                    )
                    
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('items', [])
                        
                        if not items:
                            break
                        
                        for item in items:
                            try:
                                volume = item.get('volumeInfo', {})
                                google_books_id = item.get('id')
                                
                                # Skip if already in database
                                if Book.objects.filter(google_books_id=google_books_id).exists():
                                    continue
                                
                                # Get best quality cover image
                                image_links = volume.get('imageLinks', {})
                                cover_image = (
                                    image_links.get('extraLarge') or
                                    image_links.get('large') or
                                    image_links.get('medium') or
                                    image_links.get('thumbnail') or
                                    image_links.get('smallThumbnail') or
                                    ''
                                )
                                
                                if cover_image and cover_image.startswith('http://'):
                                    cover_image = cover_image.replace('http://', 'https://')
                                
                                # Get metadata
                                isbn_10 = None
                                isbn_13 = None
                                for identifier in volume.get('industryIdentifiers', []):
                                    if identifier.get('type') == 'ISBN_10':
                                        isbn_10 = identifier.get('identifier')
                                    elif identifier.get('type') == 'ISBN_13':
                                        isbn_13 = identifier.get('identifier')
                                
                                book_data = {
                                    'title': volume.get('title', 'No title available'),
                                    'authors': ', '.join(volume.get('authors', ['Unknown author'])),
                                    'description': volume.get('description', 'No description available'),
                                    'categories': ', '.join(volume.get('categories', [])),
                                    'cover_image': cover_image,
                                    'google_books_id': google_books_id,
                                    'isbn_10': isbn_10,
                                    'isbn_13': isbn_13,
                                    'pages': volume.get('pageCount'),
                                    'publisher': volume.get('publisher'),
                                    'publication_date': volume.get('publishedDate'),
                                    'language': volume.get('language', 'en'),
                                    'preview_link': volume.get('previewLink'),
                                    'info_link': volume.get('infoLink'),
                                    'average_rating': volume.get('averageRating'),
                                    'ratings_count': volume.get('ratingsCount'),
                                }
                                
                                all_books.append(book_data)
                                
                            except Exception as e:
                                continue
                        
                        if len(items) < max_results_per_page:
                            break
                    else:
                        if page == 0:
                            messages.error(request, "Error connecting to Google Books API. Please try again.")
                        break
                
                books = all_books
                
            except requests.exceptions.RequestException:
                messages.error(request, "Network error occurred. Please try again.")
            except Exception:
                messages.error(request, "An unexpected error occurred. Please try again.")
        
        return render(request, 'books/search_google_books.html', {
            'books': books,
            'query': query,
            'search_type': search_type
        })
    
    return render(request, 'books/search_google_books.html')

@login_required
def add_to_cart(request, book_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
    try:
        book = get_object_or_404(Book, id=book_id, status='available')
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            book=book,
            defaults={'quantity': 1}
        )
        
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        
        message = f'"{book.title}" added to cart!'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_total': cart.total_items,
                'item_total': float(cart_item.total_price),
                'cart_total_price': float(cart.total_price)
            })
        else:
            messages.success(request, message)
            return redirect('books:book_detail', slug=book.slug)
            
    except Book.DoesNotExist:
        error_msg = 'Book not found or unavailable'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=404)
        else:
            messages.error(request, error_msg)
            return redirect('books:all_books')
    
    except Exception as e:
        error_msg = 'Error adding book to cart. Please try again.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        else:
            messages.error(request, error_msg)
            return redirect('books:all_books')
        
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'books/cart.html', {'cart': cart})

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        data = json.loads(request.body)
        new_quantity = data.get('quantity', 1)
        
        if new_quantity > 0:
            cart_item.quantity = new_quantity
            cart_item.save()
            
            return JsonResponse({
                'success': True,
                'item_total': float(cart_item.total_price),
                'cart_total': float(cart_item.cart.total_price)
            })
        else:
            cart_item.delete()
            return JsonResponse({
                'success': True,
                'item_deleted': True,
                'cart_total': float(cart_item.cart.total_price)
            })
    
    return JsonResponse({'success': False})

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    book_title = cart_item.book.title
    cart_item.delete()
    
    messages.success(request, f'"{book_title}" removed from cart!')
    return redirect('books:cart')