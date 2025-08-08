import paypalrestsdk
from django.conf import settings
from decimal import Decimal

class PayPalService:
    def __init__(self):
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })
    
    def create_payment(self, order, return_url, cancel_url):
        """Create a PayPal payment"""
        
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [
                        {
                            "name": item.book.title,
                            "sku": str(item.book.id),
                            "price": str(item.price),
                            "currency": "USD",
                            "quantity": item.quantity
                        } for item in order.items.all()
                    ]
                },
                "amount": {
                    "total": str(order.total_amount),
                    "currency": "USD",
                    "details": {
                        "subtotal": str(order.subtotal),
                        "tax": str(order.tax_amount),
                        "shipping": str(order.shipping_cost),
                        "shipping_discount": str(-order.discount_amount) if order.discount_amount > 0 else "0.00"
                    }
                },
                "description": f"Order #{order.order_id}"
            }]
        })
        
        if payment.create():
            return payment
        else:
            raise Exception(f"PayPal payment creation failed: {payment.error}")
    
    def execute_payment(self, payment_id, payer_id):
        """Execute an approved PayPal payment"""
        
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            return payment
        else:
            raise Exception(f"PayPal payment execution failed: {payment.error}")
    
    def get_payment_details(self, payment_id):
        """Get PayPal payment details"""
        return paypalrestsdk.Payment.find(payment_id)
