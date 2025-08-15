# wishlist/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from books.models import Book
from .models import WishlistItem, WishlistCollection, WishlistCollectionItem

@login_required
def wishlist(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('book')
    
    paginator = Paginator(wishlist_items, 12)
    page_number = request.GET.get('page')
    items = paginator.get_page(page_number)
    
    return render(request, 'wishlist/wishlist.html', {'items': items})

@login_required
def add_to_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    wishlist_item, created = WishlistItem.objects.get_or_create(
        user=request.user,
        book=book
    )
    
    if created:
        message = f'"{book.title}" added to your wishlist!'
        success = True
    else:
        message = f'"{book.title}" is already in your wishlist!'
        success = False
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'in_wishlist': True
        })
    
    messages.success(request, message)
    return redirect('books:book_detail', slug=book.slug)

@login_required
def toggle_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    wishlist_item = WishlistItem.objects.filter(user=request.user, book=book).first()
    
    if wishlist_item:
        # Remove from wishlist
        wishlist_item.delete()
        message = f'"{book.title}" removed from your wishlist!'
        in_wishlist = False
    else:
        # Add to wishlist
        WishlistItem.objects.create(user=request.user, book=book)
        message = f'"{book.title}" added to your wishlist!'
        in_wishlist = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': message,
            'in_wishlist': in_wishlist
        })
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'books:home'))

@login_required
def remove_from_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    try:
        wishlist_item = WishlistItem.objects.get(user=request.user, book=book)
        wishlist_item.delete()
        message = f'"{book.title}" removed from your wishlist!'
        success = True
    except WishlistItem.DoesNotExist:
        message = f'"{book.title}" was not in your wishlist!'
        success = False
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': success,
            'message': message,
            'in_wishlist': False
        })
    
    messages.success(request, message)
    return redirect('wishlist:wishlist')

@login_required
def move_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    try:
        wishlist_item = WishlistItem.objects.get(user=request.user, book=book)
        
        # Add to cart
        from books.models import Cart, CartItem
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            book=book,
            defaults={'quantity': 1}
        )
        
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Remove from wishlist
        wishlist_item.delete()
        
        messages.success(request, f'"{book.title}" moved to cart!')
        
    except WishlistItem.DoesNotExist:
        messages.error(request, f'"{book.title}" was not in your wishlist!')
    
    return redirect('wishlist:wishlist')

@login_required
def collections(request):
    collections = WishlistCollection.objects.filter(user=request.user)
    return render(request, 'wishlist/collections.html', {'collections': collections})

@login_required
def collection_detail(request, collection_id):
    collection = get_object_or_404(WishlistCollection, id=collection_id, user=request.user)
    items = WishlistCollectionItem.objects.filter(collection=collection).select_related('book')
    
    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    collection_items = paginator.get_page(page_number)
    
    context = {
        'collection': collection,
        'items': collection_items,
    }
    
    return render(request, 'wishlist/collection_detail.html', context)




# Add these imports at the top of your existing wishlist/views.py
from django.views.decorators.http import require_POST
from django.db.models import Q
import json

# Add these views to your existing wishlist/views.py file (after your existing views)

@login_required
@require_POST
def create_collection(request):
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    privacy = request.POST.get('privacy', 'private')
    
    if name:
        collection = WishlistCollection.objects.create(
            user=request.user,
            name=name,
            description=description,
            privacy=privacy
        )
        messages.success(request, f'Collection "{name}" created successfully!')
    else:
        messages.error(request, 'Collection name is required.')
    
    return redirect('wishlist:collections')

@login_required
@require_POST
def edit_collection(request, collection_id):
    collection = get_object_or_404(WishlistCollection, id=collection_id, user=request.user)
    
    collection.name = request.POST.get('name', collection.name)
    collection.description = request.POST.get('description', collection.description)
    collection.privacy = request.POST.get('privacy', collection.privacy)
    collection.save()
    
    messages.success(request, 'Collection updated successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('wishlist:collection_detail', collection_id=collection.id)

@login_required
@require_POST
def delete_collection(request, collection_id):
    collection = get_object_or_404(WishlistCollection, id=collection_id, user=request.user)
    collection_name = collection.name
    collection.delete()
    
    messages.success(request, f'Collection "{collection_name}" deleted successfully!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('wishlist:collections')

@login_required
def get_available_books(request, collection_id):
    collection = get_object_or_404(WishlistCollection, id=collection_id, user=request.user)
    
    # Get books from wishlist that are not in this collection
    wishlist_books = WishlistItem.objects.filter(user=request.user).select_related('book')
    collection_book_ids = collection.books.values_list('id', flat=True)
    available_books = wishlist_books.exclude(book__id__in=collection_book_ids)
    
    books_data = [{
        'id': item.book.id,
        'title': item.book.title,
        'author': ', '.join([author.name for author in item.book.authors.all()])
    } for item in available_books]
    
    return JsonResponse({'books': books_data})

@login_required
@require_POST
def add_books_to_collection(request, collection_id):
    collection = get_object_or_404(WishlistCollection, id=collection_id, user=request.user)
    
    data = json.loads(request.body)
    book_ids = data.get('book_ids', [])
    
    added_count = 0
    for book_id in book_ids:
        book = get_object_or_404(Book, id=book_id)
        # Check if user has this book in wishlist
        if WishlistItem.objects.filter(user=request.user, book=book).exists():
            WishlistCollectionItem.objects.get_or_create(
                collection=collection,
                book=book,
                defaults={'priority': 1}
            )
            added_count += 1
    
    return JsonResponse({
        'success': True,
        'message': f'{added_count} books added to collection'
    })

@login_required
@require_POST
def update_item_priority(request, item_id):
    item = get_object_or_404(WishlistCollectionItem, id=item_id, collection__user=request.user)
    
    data = json.loads(request.body)
    priority = data.get('priority', 1)
    
    item.priority = max(1, min(5, int(priority)))  # Ensure priority is between 1-5
    item.save()
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def update_item_notes(request, item_id):
    item = get_object_or_404(WishlistCollectionItem, id=item_id, collection__user=request.user)
    
    data = json.loads(request.body)
    notes = data.get('notes', '')
    
    item.notes = notes
    item.save()
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def remove_from_collection(request, item_id):
    item = get_object_or_404(WishlistCollectionItem, id=item_id, collection__user=request.user)
    item.delete()
    
    return JsonResponse({'success': True})