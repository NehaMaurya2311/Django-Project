# paypal_integration/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from orders.models import Order, OrderTracking
from warehouse.models import Stock, StockMovement
from .models import PayPalPayment
from .services import PayPalService

@login_required
def payment_options(request, order_id):
    """Display payment options for an order"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.payment_status == 'paid':
        messages.info(request, 'This order has already been paid.')
        return redirect('orders:order_detail', order_id=order_id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'paypal_integration/payment_options.html', context)

@login_required
def create_payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.payment_status == 'paid':
        messages.info(request, 'This order has already been paid.')
        return redirect('orders:order_detail', order_id=order_id)
    
    try:
        paypal_service = PayPalService()
        
        return_url = request.build_absolute_uri(reverse('paypal_integration:execute_payment', args=[order_id]))
        cancel_url = request.build_absolute_uri(reverse('paypal_integration:payment_cancelled', args=[order_id]))
        
        payment = paypal_service.create_payment(order, return_url, cancel_url)
        
        # Save PayPal payment record
        paypal_payment, created = PayPalPayment.objects.get_or_create(
            order=order,
            defaults={
                'paypal_payment_id': payment.id,
                'amount': order.total_amount,
                'paypal_response': payment.to_dict()
            }
        )
        
        if not created:
            paypal_payment.paypal_payment_id = payment.id
            paypal_payment.paypal_response = payment.to_dict()
            paypal_payment.save()
        
        # Get approval URL
        for link in payment.links:
            if link.rel == "approval_url":
                paypal_payment.approval_url = link.href
                paypal_payment.save()
                return redirect(link.href)
        
        messages.error(request, 'Error creating PayPal payment.')
        return redirect('paypal_integration:payment_options', order_id=order_id)
        
    except Exception as e:
        messages.error(request, f'Payment creation failed: {str(e)}')
        return redirect('paypal_integration:payment_options', order_id=order_id)

@login_required
def execute_payment(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    
    if not payment_id or not payer_id:
        messages.error(request, 'Invalid payment parameters.')
        return redirect('paypal_integration:payment_options', order_id=order_id)
    
    try:
        paypal_payment = get_object_or_404(PayPalPayment, order=order, paypal_payment_id=payment_id)
        
        paypal_service = PayPalService()
        executed_payment = paypal_service.execute_payment(payment_id, payer_id)
        
        if executed_payment.state == 'approved':
            # Update payment record
            paypal_payment.paypal_payer_id = payer_id
            paypal_payment.status = 'completed'
            paypal_payment.completed_at = timezone.now()
            paypal_payment.paypal_response = executed_payment.to_dict()
            paypal_payment.save()
            
            # Update order
            order.payment_status = 'paid'
            order.payment_method = 'PayPal'
            order.payment_transaction_id = payment_id
            order.status = 'confirmed'
            order.save()
            
            # Convert reserved stock to actual stock reduction
            for item in order.items.all():
                try:
                    stock = Stock.objects.get(book=item.book)
                    # Remove from reserved and actual quantity
                    stock.reserved_quantity = max(0, stock.reserved_quantity - item.quantity)
                    stock.quantity = max(0, stock.quantity - item.quantity)
                    stock.save()
                    
                    # Create stock movement record
                    StockMovement.objects.create(
                        stock=stock,
                        movement_type='out',
                        quantity=-item.quantity,
                        reference=order.order_id,
                        reason='Order fulfillment',
                        performed_by=None
                    )
                except Stock.DoesNotExist:
                    pass
            
            # Add order tracking
            OrderTracking.objects.create(
                order=order,
                status='order_confirmed',
                description='Payment received and order confirmed.'
            )
            
            messages.success(request, f'Payment successful! Your order #{order.order_id} has been confirmed.')
            return redirect('paypal_integration:payment_success', order_id=order_id)
        
        else:
            messages.error(request, 'Payment was not approved.')
            return redirect('paypal_integration:payment_options', order_id=order_id)
            
    except Exception as e:
        messages.error(request, f'Payment execution failed: {str(e)}')
        return redirect('paypal_integration:payment_options', order_id=order_id)

@login_required
def payment_cancelled(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    try:
        paypal_payment = PayPalPayment.objects.get(order=order)
        paypal_payment.status = 'cancelled'
        paypal_payment.save()
    except PayPalPayment.DoesNotExist:
        pass
    
    messages.info(request, 'Payment was cancelled. You can try again when ready.')
    return redirect('paypal_integration:payment_options', order_id=order_id)

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'paypal_integration/payment_success.html', context)