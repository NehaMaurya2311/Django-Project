# books/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Book, Category, Cart, CartItem, Author, Publisher
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
        from wishlist.models import WishlistItem
        in_wishlist = WishlistItem.objects.filter(user=request.user, book=book).exists()
    
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
