# warehouse/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Stock, StockMovement, CategoryStock, InventoryAudit
from books.models import Book, Category

def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

@login_required
@user_passes_test(is_staff_or_admin)
def warehouse_dashboard(request):
    # Key metrics
    total_books = Stock.objects.count()
    total_quantity = Stock.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    out_of_stock = Stock.objects.filter(quantity=0).count()
    low_stock = Stock.objects.filter(
        Q(quantity__lte=F('reorder_level')) & Q(quantity__gt=0)
    ).count()
    
    # Recent movements
    recent_movements = StockMovement.objects.select_related('stock__book').order_by('-created_at')[:10]
    
    # Category-wise stock with updated stats
    category_stats = []
    for category in Category.objects.filter(is_active=True):
        category_stock, created = CategoryStock.objects.get_or_create(category=category)
        if created or True:  # Always update stats for accurate display
            category_stock.update_stats()
        category_stats.append(category_stock)
    
    context = {
        'total_books': total_books,
        'total_quantity': total_quantity,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'recent_movements': recent_movements,
        'category_stats': category_stats,
    }
    
    return render(request, 'warehouse/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def stock_list(request):
    stocks_list = Stock.objects.select_related('book', 'book__category').order_by('book__title')
    
    # Filters
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    if category_filter:
        stocks_list = stocks_list.filter(book__category__slug=category_filter)
    
    if status_filter:
        if status_filter == 'out_of_stock':
            stocks_list = stocks_list.filter(quantity=0)
        elif status_filter == 'low_stock':
            stocks_list = stocks_list.filter(
                Q(quantity__lte=F('reorder_level')) & Q(quantity__gt=0)
            )
        elif status_filter == 'in_stock':
            stocks_list = stocks_list.filter(quantity__gt=F('reorder_level'))
    
    if search_query:
        stocks_list = stocks_list.filter(
            Q(book__title__icontains=search_query) |
            Q(book__isbn__icontains=search_query) |
            Q(book__authors__name__icontains=search_query)
        ).distinct()
    
    paginator = Paginator(stocks_list, 20)
    page_number = request.GET.get('page')
    stocks = paginator.get_page(page_number)
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'stocks': stocks,
        'categories': categories,
        'current_category': category_filter,
        'current_status': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'warehouse/stock_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def stock_detail(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    movements = StockMovement.objects.filter(stock=stock).order_by('-created_at')[:20]
    
    context = {
        'stock': stock,
        'movements': movements,
    }
    
    return render(request, 'warehouse/stock_detail.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def add_stock(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        reference = request.POST.get('reference', '')
        reason = request.POST.get('reason', '')
        
        if quantity > 0:
            StockMovement.objects.create(
                stock=stock,
                movement_type='in',
                quantity=quantity,
                reference=reference,
                reason=reason,
                performed_by=request.user
            )
            
            messages.success(request, f'Added {quantity} units to {stock.book.title}')
        else:
            messages.error(request, 'Quantity must be greater than 0')
    
    return redirect('warehouse:stock_detail', stock_id=stock_id)

@login_required
@user_passes_test(is_staff_or_admin)
def remove_stock(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        reference = request.POST.get('reference', '')
        reason = request.POST.get('reason', '')
        movement_type = request.POST.get('movement_type', 'out')
        
        if quantity > 0 and quantity <= stock.available_quantity:
            StockMovement.objects.create(
                stock=stock,
                movement_type=movement_type,
                quantity=-quantity,  # Negative for outgoing
                reference=reference,
                reason=reason,
                performed_by=request.user
            )
            
            messages.success(request, f'Removed {quantity} units from {stock.book.title}')
        else:
            messages.error(request, 'Invalid quantity or insufficient stock')
    
    return redirect('warehouse:stock_detail', stock_id=stock_id)

@login_required
@user_passes_test(is_staff_or_admin)
def low_stock_report(request):
    low_stock_items = Stock.objects.filter(
        Q(quantity__lte=F('reorder_level')) & Q(quantity__gt=0)
    ).select_related('book', 'book__category').order_by('quantity')
    
    out_of_stock_count = Stock.objects.filter(quantity=0).count()
    
    return render(request, 'warehouse/low_stock_report.html', {
        'low_stock_items': low_stock_items,
        'out_of_stock_count': out_of_stock_count
    })