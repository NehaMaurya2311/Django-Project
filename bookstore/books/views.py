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
import json
import requests

from .models import Book, Category, Cart, CartItem, Author, Publisher, SubCategory
from .forms import BookForm, BookFilterForm
from warehouse.models import Stock

def home(request):
    featured_books = Book.objects.filter(is_featured=True, status='available')[:8]
    bestseller_books = Book.objects.filter(is_bestseller=True, status='available')[:8]
    sale_books = Book.objects.filter(is_on_sale=True, status='available')[:8]
    categories = Category.objects.filter(is_active=True)[:8]
    
    context = {
        'featured_books': featured_books,
        'bestseller_books': bestseller_books,
        'sale_books': sale_books,
        'categories': categories,
    }
    return render(request, 'books/home.html', context)

def normalize_category_name(name):
    """Normalize category names for better matching"""
    # Remove extra whitespace and convert to title case
    name = ' '.join(name.split()).title()
    
    # Handle common variations
    replacements = {
        # Biography variations
        'Biography & Autobiography': 'Biography',
        'Biographies & Autobiographies': 'Biography',
        'Autobiography': 'Biography',
        'Autobiographies': 'Biography',
        'Biographical': 'Biography',
        
        # Fiction genres
        'Romance Fiction': 'Romance',
        'Fantasy Fiction': 'Fantasy',
        'Science Fiction & Fantasy': 'Science Fiction',
        'Sci-Fi': 'Science Fiction',
        'Mystery Fiction': 'Mystery',
        'Horror Fiction': 'Horror',
        'Thriller Fiction': 'Thriller',
        'Adventure Fiction': 'Adventure',
        'Historical Fiction': 'Historical Fiction',
        
        # Young Adult variations
        'Juvenile Fiction': 'Young Adult Fiction',
        'Young Adult Literature': 'Young Adult Fiction',
        'Ya Fiction': 'Young Adult Fiction',
        'Teen Fiction': 'Young Adult Fiction',
        'Teenage Fiction': 'Young Adult Fiction',
        
        # Children's books variations
        'Children\'S Books': 'Children\'s Books',
        'Children\'S Fiction': 'Children\'s Books',
        'Children\'S Literature': 'Children\'s Books',
        'Children\'S Poetry': 'Children\'s Poetry',
        'Childrens Books': 'Children\'s Books',
        'Childrens Fiction': 'Children\'s Books',
        'Childrens Poetry': 'Children\'s Poetry',
        'Kids Books': 'Children\'s Books',
        
        # Non-fiction variations
        'History & Geography': 'History',
        'Health & Fitness': 'Health & Fitness',
        'Self Help': 'Self-Help',
        'Self-Help & Relationships': 'Self-Help',
        'Business & Economics': 'Business',
        'Computers & Technology': 'Technology',
        'Religion & Spirituality': 'Religion',
        'Philosophy & Religion': 'Philosophy',
        
        # Education
        'Education & Teaching': 'Education',
        'Study Aids': 'Education',
        'Reference': 'Reference',
        
        # Arts
        'Art & Design': 'Art & Design',
        'Music & Arts': 'Arts',
        'Photography': 'Photography',
        
        # Other common variations
        'True Crime': 'Crime',
        'Political Science': 'Politics',
        'Psychology & Counseling': 'Psychology',
        'Travel & Tourism': 'Travel',
        'Cooking & Food': 'Cooking',
        'Sports & Recreation': 'Sports',
    }
    
    return replacements.get(name, name)

def create_categories_from_string(category_string):
    """Helper function to create categories from comma-separated string with better normalization"""
    if not category_string:
        return []
    
    categories = []
    category_names = []
    
    # Split by common delimiters
    for delimiter in [',', '/', '|', ';']:
        if delimiter in category_string:
            category_names = category_string.split(delimiter)
            break
    else:
        category_names = [category_string]
    
    for cat_name in category_names:
        cat_name = cat_name.strip()
        if cat_name:
            # Normalize the category name
            normalized_name = normalize_category_name(cat_name)
            
            # Try to find existing category first (case-insensitive)
            existing_category = Category.objects.filter(
                name__iexact=normalized_name
            ).first()
            
            if existing_category:
                categories.append(existing_category)
            else:
                # Create new category with normalized name
                category, created = Category.objects.get_or_create(
                    name=normalized_name,
                    defaults={'slug': slugify(normalized_name)}
                )
                categories.append(category)
    
    return categories

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
    
    # Get available authors for filter
    authors = Author.objects.filter(books__category=category).distinct()
    
    context = {
        'category': category,
        'books': books,
        'authors': authors,
    }
    return render(request, 'books/category_books.html', context)

def subcategory_books(request, category_slug, subcategory_slug):
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    subcategory = get_object_or_404(SubCategory, slug=subcategory_slug, category=category, is_active=True)
    books_list = Book.objects.filter(subcategory=subcategory, status='available').order_by('-created_at')
    
    # Apply the same filters as category_books
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
    
    authors = Author.objects.filter(books__subcategory=subcategory).distinct()
    
    context = {
        'category': category,
        'subcategory': subcategory,
        'books': books,
        'authors': authors,
    }
    return render(request, 'books/subcategory_books.html', context)

def all_books(request):
    books_list = Book.objects.filter(status='available').order_by('-created_at')
    
    # Apply filters
    price_filter = request.GET.get('price')
    format_filter = request.GET.get('format')
    author_filter = request.GET.get('author')
    category_filter = request.GET.get('category')
    
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
    
    paginator = Paginator(books_list, 24)  # Show more books on all books page
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    # Get all filters data
    categories = Category.objects.filter(is_active=True)
    authors = Author.objects.filter(books__isnull=False).distinct()
    
    context = {
        'books': books,
        'categories': categories,
        'authors': authors,
    }
    return render(request, 'books/all_books.html', context)

def search_books(request):
    query = request.GET.get('q', '')
    books_list = Book.objects.filter(status='available')
    
    if query:
        books_list = books_list.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(description__icontains=query) |
            Q(isbn__icontains=query) |
            Q(isbn13__icontains=query)
        ).distinct()
    
    paginator = Paginator(books_list, 12)
    page_number = request.GET.get('page')
    books = paginator.get_page(page_number)
    
    context = {
        'books': books,
        'query': query,
        'total_results': books_list.count(),
    }
    return render(request, 'books/search_results.html', context)

@login_required
def add_book(request):
    if request.method == 'POST':
        google_books_id = request.POST.get('google_books_id')
        
        if google_books_id:
            # Check if book already exists
            if Book.objects.filter(google_books_id=google_books_id).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Book already exists'}, status=400)
                messages.warning(request, 'This book already exists in the library!')
                return redirect('books:search_google_books')

            # Create book from API data
            try:
                # Create the book
                book = Book(
                    title=request.POST.get('title'),
                    description=request.POST.get('description'),
                    google_books_id=google_books_id,
                    price=request.POST.get('price', 0.00),
                    slug=slugify(request.POST.get('title'))
                )
                
                # Handle cover image
                cover_image_url = request.POST.get('cover_image')
                if cover_image_url:
                    book.cover_image = cover_image_url
                
                # Save the book first
                book.save()
                
                # Handle authors
                authors_string = request.POST.get('authors', '')
                authors = create_authors_from_string(authors_string)
                book.authors.set(authors)
                
                # Handle categories
                categories_string = request.POST.get('categories', '')
                categories = create_categories_from_string(categories_string)
                if categories:
                    book.category = categories[0]  # Set main category to first one
                    book.save()
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'book_id': book.pk})
                    
                messages.success(request, f'Book "{book.title}" added successfully!')
                return redirect('books:book_detail', slug=book.slug)
                
            except IntegrityError:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Duplicate book'}, status=400)
                messages.error(request, 'This book already exists.')
                
            return redirect('books:search_google_books')
        
        # Handle regular form submission
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
    # Only superusers can delete books
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
                # Get multiple pages of results
                all_books = []
                max_results_per_page = 40
                max_pages = 5
                
                for page in range(max_pages):
                    start_index = page * max_results_per_page
                    
                    # Build query based on search type
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
                                
                                # Get cover image with fallback options
                                image_links = volume.get('imageLinks', {})
                                cover_image = (
                                    image_links.get('large') or
                                    image_links.get('medium') or
                                    image_links.get('thumbnail') or
                                    image_links.get('smallThumbnail') or
                                    ''
                                )
                                
                                # Convert HTTP to HTTPS for security
                                if cover_image and cover_image.startswith('http://'):
                                    cover_image = cover_image.replace('http://', 'https://')
                                
                                book_data = {
                                    'title': volume.get('title', 'No title available'),
                                    'authors': ', '.join(volume.get('authors', ['Unknown author'])),
                                    'description': volume.get('description', 'No description available'),
                                    'categories': ', '.join(volume.get('categories', [])),
                                    'cover_image': cover_image,
                                    'google_books_id': item.get('id')
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






# Cart views remain the same
@login_required
def add_to_cart(request, book_id):
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
    
    messages.success(request, f'"{book.title}" added to cart!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'"{book.title}" added to cart!',
            'cart_total': cart.total_items
        })
    
    return redirect('books:book_detail', slug=book.slug)

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