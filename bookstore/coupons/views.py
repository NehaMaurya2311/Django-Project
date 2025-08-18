# coupons/views.py - Updated with Sales System
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from .models import Coupon, BookSale, BookSaleItem
from books.models import Book, Cart
import json

@login_required
def validate_coupon(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').upper()
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            
            # Get user's cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_items = cart.items.all()
            
            if not cart_items.exists():
                return JsonResponse({
                    'valid': False,
                    'message': 'Your cart is empty'
                })
            
            is_valid, message = coupon.can_use(request.user, cart.subtotal, cart_items)
            
            if is_valid:
                discount_amount = coupon.calculate_discount(cart_items)
                new_total = cart.subtotal - discount_amount
                
                return JsonResponse({
                    'valid': True,
                    'message': 'Coupon applied successfully!',
                    'discount_amount': float(discount_amount),
                    'discount_type': coupon.discount_type,
                    'new_total': float(new_total),
                    'original_total': float(cart.subtotal)
                })
            else:
                return JsonResponse({
                    'valid': False,
                    'message': message
                })
                
        except Coupon.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid coupon code'
            })
    
    return JsonResponse({'valid': False, 'message': 'Invalid request'})

@login_required
def available_coupons(request):
    """Show available coupons for the user"""
    # Get user's cart for coupon applicability
    cart, created = Cart.objects.get_or_create(user=request.user)
    applicable_coupons = cart.get_applicable_coupons(request.user)
    
    context = {
        'applicable_coupons': applicable_coupons,
        'cart': cart
    }
    return render(request, 'coupons/available_coupons.html', context)

def sale_books(request):
    """Display all books currently on sale"""
    current_time = timezone.now()
    
    # Get all active sale items
    sale_items = BookSaleItem.objects.select_related('book', 'sale').filter(
        sale__is_active=True,
        sale__valid_from__lte=current_time,
        sale__valid_to__gte=current_time
    ).order_by('-sale__created_at')
    
    # Get unique books on sale
    books_on_sale = []
    seen_books = set()
    
    for sale_item in sale_items:
        if sale_item.book.id not in seen_books:
            books_on_sale.append({
                'book': sale_item.book,
                'sale_item': sale_item,
                'original_price': sale_item.book.price,
                'sale_price': sale_item.get_sale_price(),
                'discount_percentage': sale_item.get_discount_percentage()
            })
            seen_books.add(sale_item.book.id)
    
    # Get current active sales for context
    active_sales = BookSale.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_to__gte=current_time
    )
    
    context = {
        'books_on_sale': books_on_sale,
        'active_sales': active_sales,
        'total_books': len(books_on_sale)
    }
    
    return render(request, 'coupons/sale_books.html', context)

@login_required
def cart_coupons_ajax(request):
    """AJAX endpoint to get applicable coupons for cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    applicable_coupons = cart.get_applicable_coupons(request.user)
    
    coupons_data = []
    for item in applicable_coupons:
        coupon = item['coupon']
        coupons_data.append({
            'code': coupon.code,
            'name': coupon.name,
            'description': coupon.description,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'can_use': item['can_use'],
            'message': item['message'],
            'discount_amount': float(item['discount_amount']),
            'min_order_amount': float(coupon.min_order_amount)
        })
    
    return JsonResponse({
        'coupons': coupons_data,
        'cart_total': float(cart.subtotal)
    })

def get_book_sale_info(request, book_id):
    """Get sale information for a specific book"""
    try:
        book = Book.objects.get(id=book_id)
        
        response_data = {
            'is_on_sale': book.is_on_sale_now,
            'original_price': float(book.price),
            'current_price': float(book.effective_price),
            'discount_percentage': book.sale_discount_percentage,
            'has_coupons': book.has_available_coupons
        }
        
        if book.current_sale:
            response_data.update({
                'sale_name': book.current_sale.sale.name,
                'sale_description': book.current_sale.sale.description,
                'sale_valid_to': book.current_sale.sale.valid_to.isoformat()
            })
        
        return JsonResponse(response_data)
        
    except Book.DoesNotExist:
        return JsonResponse({'error': 'Book not found'}, status=404)