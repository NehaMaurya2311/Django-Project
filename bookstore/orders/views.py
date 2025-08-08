# orders/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from books.models import Cart, CartItem
from warehouse.models import Stock, StockMovement
from coupons.models import Coupon, CouponUsage
from .models import Order, OrderItem, OrderTracking, Return, ReturnItem
from .forms import CheckoutForm, ReturnRequestForm
from decimal import Decimal
import json

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty!')
        return redirect('books:cart')
    
    # Check stock availability
    for item in cart.items.all():
        try:
            stock = Stock.objects.get(book=item.book)
            if stock.available_quantity < item.quantity:
                messages.error(request, f'Only {stock.available_quantity} units of "{item.book.title}" are available.')
                return redirect('books:cart')
        except Stock.DoesNotExist:
            messages.error(request, f'"{item.book.title}" is currently out of stock.')
            return redirect('books:cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create order
                    order = Order.objects.create(
                        user=request.user,
                        billing_first_name=form.cleaned_data['billing_first_name'],
                        billing_last_name=form.cleaned_data['billing_last_name'],
                        billing_email=form.cleaned_data['billing_email'],
                        billing_phone=form.cleaned_data['billing_phone'],
                        billing_address=form.cleaned_data['billing_address'],
                        billing_city=form.cleaned_data['billing_city'],
                        billing_state=form.cleaned_data['billing_state'],
                        billing_pincode=form.cleaned_data['billing_pincode'],
                        
                        shipping_first_name=form.cleaned_data.get('shipping_first_name') or form.cleaned_data['billing_first_name'],
                        shipping_last_name=form.cleaned_data.get('shipping_last_name') or form.cleaned_data['billing_last_name'],
                        shipping_address=form.cleaned_data.get('shipping_address') or form.cleaned_data['billing_address'],
                        shipping_city=form.cleaned_data.get('shipping_city') or form.cleaned_data['billing_city'],
                        shipping_state=form.cleaned_data.get('shipping_state') or form.cleaned_data['billing_state'],
                        shipping_pincode=form.cleaned_data.get('shipping_pincode') or form.cleaned_data['billing_pincode'],
                        
                        subtotal=cart.total_price,
                        total_amount=cart.total_price,  # Will be updated with shipping/tax
                        coupon_code=form.cleaned_data.get('coupon_code', ''),
                        notes=form.cleaned_data.get('notes', ''),
                    )
                    
                    # Create order items and reserve stock
                    for cart_item in cart.items.all():
                        OrderItem.objects.create(
                            order=order,
                            book=cart_item.book,
                            quantity=cart_item.quantity,
                            price=cart_item.book.price,
                        )
                        
                        # Reserve stock
                        stock = Stock.objects.get(book=cart_item.book)
                        stock.reserved_quantity += cart_item.quantity
                        stock.save()
                    
                    # Apply coupon if provided
                    coupon_code = form.cleaned_data.get('coupon_code')
                    if coupon_code:
                        try:
                            coupon = Coupon.objects.get(
                                code=coupon_code,
                                is_active=True,
                                valid_from__lte=timezone.now(),
                                valid_to__gte=timezone.now()
                            )
                            
                            if coupon.can_use(request.user):
                                discount = coupon.calculate_discount(order.subtotal)
                                order.discount_amount = discount
                                order.total_amount = order.subtotal - discount
                                order.save()
                                
                                # Record coupon usage
                                CouponUsage.objects.create(
                                    coupon=coupon,
                                    user=request.user,
                                    order=order,
                                    discount_amount=discount
                                )
                        except Coupon.DoesNotExist:
                            pass
                    
                    # Create initial tracking
                    OrderTracking.objects.create(
                        order=order,
                        status='order_placed',
                        description='Order has been placed successfully.'
                    )
                    
                    # Clear cart
                    cart.items.all().delete()
                    
                    messages.success(request, f'Order #{order.order_id} placed successfully!')
                    return redirect('orders:order_detail', order_id=order.order_id)
                    
            except Exception as e:
                messages.error(request, 'An error occurred while processing your order. Please try again.')
                return redirect('books:cart')
    else:
        # Pre-populate form with user data
        initial_data = {
            'billing_first_name': request.user.first_name,
            'billing_last_name': request.user.last_name,
            'billing_email': request.user.email,
            'billing_phone': request.user.phone,
            'billing_address': request.user.address,
            'billing_city': request.user.city,
            'billing_state': request.user.state,
            'billing_pincode': request.user.pincode,
        }
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart': cart,
    }
    
    return render(request, 'orders/checkout.html', context)

@login_required
def order_list(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
    
    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    return render(request, 'orders/order_list.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.status in ['pending', 'confirmed']:
        order.status = 'cancelled'
        order.save()
        
        # Release reserved stock
        for item in order.items.all():
            try:
                stock = Stock.objects.get(book=item.book)
                stock.reserved_quantity = max(0, stock.reserved_quantity - item.quantity)
                stock.save()
            except Stock.DoesNotExist:
                pass
        
        OrderTracking.objects.create(
            order=order,
            status='cancelled',
            description='Order cancelled by customer.'
        )
        
        messages.success(request, f'Order #{order.order_id} has been cancelled.')
    else:
        messages.error(request, 'This order cannot be cancelled.')
    
    return redirect('orders:order_detail', order_id=order_id)

@login_required
def request_return(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.status != 'delivered':
        messages.error(request, 'Returns can only be requested for delivered orders.')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.save()
            
            # Add all order items to return (simplified - in real app, allow selection)
            for order_item in order.items.all():
                ReturnItem.objects.create(
                    return_request=return_request,
                    order_item=order_item,
                    quantity=order_item.quantity
                )
            
            messages.success(request, f'Return request #{return_request.return_id} submitted successfully!')
            return redirect('orders:order_detail', order_id=order_id)
    else:
        form = ReturnRequestForm()
    
    return render(request, 'orders/request_return.html', {'form': form, 'order': order})
