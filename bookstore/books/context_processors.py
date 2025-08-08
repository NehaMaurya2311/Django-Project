# books/context_processors.py
def cart_processor(request):
    cart_total = 0
    if request.user.is_authenticated:
        from .models import Cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart_total = cart.total_items
        except Cart.DoesNotExist:
            cart_total = 0
    
    return {'cart_total': cart_total}

def categories_processor(request):
    from .models import Category
    categories = Category.objects.filter(is_active=True)
    return {'categories': categories}