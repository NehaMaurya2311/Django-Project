# warehouse/views.py - ENHANCED VERSION with Stock Offer Management
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from .models import Stock, StockMovement, CategoryStock, InventoryAudit
from vendors.models import StockOffer, VendorProfile, OfferStatusNotification
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
    
    # Stock offer metrics - NEW
    pending_offers = StockOffer.objects.filter(status='pending').count()
    approved_offers = StockOffer.objects.filter(status='approved').count()
    today_offers = StockOffer.objects.filter(created_at__date=timezone.now().date()).count()
    
    # Recent movements
    recent_movements = StockMovement.objects.select_related('stock__book').order_by('-created_at')[:10]
    
    # Recent stock offers - NEW
    recent_offers = StockOffer.objects.select_related(
        'vendor', 'book'
    ).order_by('-created_at')[:8]
    
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
        'pending_offers': pending_offers,
        'approved_offers': approved_offers,
        'today_offers': today_offers,
        'recent_movements': recent_movements,
        'recent_offers': recent_offers,
        'category_stats': category_stats,
    }
    
    return render(request, 'warehouse/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def stock_offers_list(request):
    """List all stock offers from vendors"""
    offers_list = StockOffer.objects.select_related(
        'vendor', 'book', 'book__category', 'reviewed_by'
    ).order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    vendor_filter = request.GET.get('vendor')
    category_filter = request.GET.get('category')
    priority_filter = request.GET.get('priority')
    
    if status_filter:
        offers_list = offers_list.filter(status=status_filter)
    
    if vendor_filter:
        offers_list = offers_list.filter(vendor_id=vendor_filter)
    
    if category_filter:
        offers_list = offers_list.filter(book__category_id=category_filter)
    
    # Priority filtering based on stock levels
    if priority_filter == 'high':
        # Books that are out of stock or have no stock record
        offers_list = offers_list.filter(
            Q(book__stock__quantity=0) | Q(book__stock__isnull=True)
        )
    elif priority_filter == 'medium':
        # Books with low stock
        offers_list = offers_list.filter(
            book__stock__quantity__lte=F('book__stock__reorder_level'),
            book__stock__quantity__gt=0
        )
    
    # Pagination
    paginator = Paginator(offers_list, 15)
    page_number = request.GET.get('page')
    offers = paginator.get_page(page_number)
    
    # Add priority information to each offer
    for offer in offers:
        try:
            stock = Stock.objects.get(book=offer.book)
            if stock.quantity == 0:
                offer.priority = 'high'
                offer.priority_text = 'Out of Stock'
                offer.priority_class = 'danger'
            elif stock.quantity <= stock.reorder_level:
                offer.priority = 'medium'
                offer.priority_text = 'Low Stock'
                offer.priority_class = 'warning'
            else:
                offer.priority = 'low'
                offer.priority_text = 'Normal Stock'
                offer.priority_class = 'success'
            offer.current_stock = stock.quantity
            offer.reorder_level = stock.reorder_level
        except Stock.DoesNotExist:
            offer.priority = 'high'
            offer.priority_text = 'No Stock Record'
            offer.priority_class = 'danger'
            offer.current_stock = 0
            offer.reorder_level = 10
    
    # Get filter options
    vendors = VendorProfile.objects.filter(status='approved').order_by('business_name')
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    context = {
        'offers': offers,
        'vendors': vendors,
        'categories': categories,
        'current_status': status_filter,
        'current_vendor': vendor_filter,
        'current_category': category_filter,
        'current_priority': priority_filter,
    }
    
    return render(request, 'warehouse/stock_offers_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def vendor_offers(request, vendor_id):
    """View all offers from a specific vendor"""
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    
    offers_list = StockOffer.objects.filter(vendor=vendor).select_related(
        'book', 'book__category', 'reviewed_by'
    ).order_by('-created_at')
    
    # Status filter
    status_filter = request.GET.get('status')
    if status_filter:
        offers_list = offers_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(offers_list, 10)
    page_number = request.GET.get('page')
    offers = paginator.get_page(page_number)
    
    # Add stock information
    for offer in offers:
        try:
            stock = Stock.objects.get(book=offer.book)
            offer.current_stock = stock.quantity
            offer.reorder_level = stock.reorder_level
            offer.needs_restock = stock.quantity <= stock.reorder_level
        except Stock.DoesNotExist:
            offer.current_stock = 0
            offer.reorder_level = 10
            offer.needs_restock = True
    
    # Vendor statistics
    stats = {
        'total_offers': StockOffer.objects.filter(vendor=vendor).count(),
        'pending_offers': StockOffer.objects.filter(vendor=vendor, status='pending').count(),
        'approved_offers': StockOffer.objects.filter(vendor=vendor, status='approved').count(),
        'processed_offers': StockOffer.objects.filter(vendor=vendor, status='processed').count(),
        'total_value': StockOffer.objects.filter(
            vendor=vendor, status__in=['approved', 'processed']
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    
    context = {
        'vendor': vendor,
        'offers': offers,
        'stats': stats,
        'current_status': status_filter,
    }
    
    return render(request, 'warehouse/vendor_offers.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def offer_detail(request, offer_id):
    """View detailed information about a stock offer"""
    offer = get_object_or_404(StockOffer, id=offer_id)
    
    # Get current stock information
    try:
        stock = Stock.objects.get(book=offer.book)
        current_stock = stock.quantity
        reorder_level = stock.reorder_level
        location = stock.get_location()
    except Stock.DoesNotExist:
        current_stock = 0
        reorder_level = 10
        location = "Not Assigned"
        # Create stock record if it doesn't exist
        stock = Stock.objects.create(
            book=offer.book,
            quantity=0,
            reorder_level=10
        )
    
    # Get recent offers for the same book
    similar_offers = StockOffer.objects.filter(
        book=offer.book
    ).exclude(id=offer.id).select_related('vendor').order_by('-created_at')[:5]
    
    # Get stock movements for this book
    recent_movements = StockMovement.objects.filter(
        stock=stock
    ).order_by('-created_at')[:10]
    
    context = {
        'offer': offer,
        'stock': stock,
        'current_stock': current_stock,
        'reorder_level': reorder_level,
        'location': location,
        'similar_offers': similar_offers,
        'recent_movements': recent_movements,
    }
    
    return render(request, 'warehouse/offer_detail.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def approve_offer(request, offer_id):
    """Approve a stock offer"""
    offer = get_object_or_404(StockOffer, id=offer_id)
    
    if offer.status != 'pending':
        messages.error(request, 'This offer has already been processed.')
        return redirect('warehouse:offer_detail', offer_id=offer_id)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '').strip()
        
        with transaction.atomic():
            # Update offer status
            offer.status = 'approved'
            offer.reviewed_by = request.user
            offer.reviewed_at = timezone.now()
            if admin_notes:
                offer.admin_notes = admin_notes
            offer.save()
            
            # Create notification for vendor
            OfferStatusNotification.objects.create(
                stock_offer=offer,
                status='approved',
                message=f"Great news! Your offer for '{offer.book.title}' ({offer.quantity} copies) has been approved for ₹{offer.total_amount}. Please schedule delivery as soon as possible."
            )
            
            messages.success(
                request, 
                f'Offer approved successfully! {offer.vendor.business_name} will be notified to schedule delivery.'
            )
        
        return redirect('warehouse:offer_detail', offer_id=offer_id)
    
    return redirect('warehouse:offer_detail', offer_id=offer_id)

@login_required
@user_passes_test(is_staff_or_admin)
def reject_offer(request, offer_id):
    """Reject a stock offer"""
    offer = get_object_or_404(StockOffer, id=offer_id)
    
    if offer.status != 'pending':
        messages.error(request, 'This offer has already been processed.')
        return redirect('warehouse:offer_detail', offer_id=offer_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('warehouse:offer_detail', offer_id=offer_id)
        
        with transaction.atomic():
            # Update offer status
            offer.status = 'rejected'
            offer.reviewed_by = request.user
            offer.reviewed_at = timezone.now()
            offer.admin_notes = rejection_reason
            offer.save()
            
            # Create notification for vendor
            OfferStatusNotification.objects.create(
                stock_offer=offer,
                status='rejected',
                message=f"Your offer for '{offer.book.title}' was not accepted. Reason: {rejection_reason}"
            )
            
            messages.success(
                request, 
                f'Offer rejected successfully. {offer.vendor.business_name} has been notified.'
            )
        
        return redirect('warehouse:offer_detail', offer_id=offer_id)
    
    return redirect('warehouse:offer_detail', offer_id=offer_id)

@login_required
@user_passes_test(is_staff_or_admin)
def update_stock_location(request, stock_id):
    """Update stock location information"""
    stock = get_object_or_404(Stock, id=stock_id)
    
    if request.method == 'POST':
        location_section = request.POST.get('location_section', '').strip()
        location_row = request.POST.get('location_row', '').strip()
        location_shelf = request.POST.get('location_shelf', '').strip()
        
        # Update location
        stock.location_section = location_section
        stock.location_row = location_row
        stock.location_shelf = location_shelf
        stock.save()
        
        # Create a movement record for location update
        StockMovement.objects.create(
            stock=stock,
            movement_type='adjustment',
            quantity=0,  # No quantity change
            reference='Location Update',
            reason=f'Location updated to: {stock.get_location()}',
            performed_by=request.user
        )
        
        messages.success(
            request, 
            f'Location updated to {stock.get_location()} for "{stock.book.title}"'
        )
    
    return redirect('warehouse:stock_detail', stock_id=stock_id)

@login_required
@user_passes_test(is_staff_or_admin)
def stock_list(request):
    stocks_list = Stock.objects.select_related('book', 'book__category').order_by('book__title')
    
    # Filters
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    location_filter = request.GET.get('location')
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
    
    if location_filter:
        if location_filter == 'assigned':
            stocks_list = stocks_list.exclude(
                location_section='', location_row='', location_shelf=''
            )
        elif location_filter == 'unassigned':
            stocks_list = stocks_list.filter(
                Q(location_section='') | Q(location_row='') | Q(location_shelf='')
            )
    
    if search_query:
        stocks_list = stocks_list.filter(
            Q(book__title__icontains=search_query) |
            Q(book__isbn__icontains=search_query) |
            Q(book__authors__name__icontains=search_query) |
            Q(location_section__icontains=search_query) |
            Q(location_row__icontains=search_query) |
            Q(location_shelf__icontains=search_query)
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
        'current_location': location_filter,
        'search_query': search_query,
    }
    
    return render(request, 'warehouse/stock_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def stock_detail(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    movements = StockMovement.objects.filter(stock=stock).order_by('-created_at')[:20]
    
    # Get pending offers for this book
    pending_offers = StockOffer.objects.filter(
        book=stock.book, 
        status__in=['pending', 'approved']
    ).select_related('vendor').order_by('-created_at')
    
    context = {
        'stock': stock,
        'movements': movements,
        'pending_offers': pending_offers,
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
    
    out_of_stock_items = Stock.objects.filter(quantity=0).select_related(
        'book', 'book__category'
    ).order_by('book__title')
    
    # Get pending offers for these items
    low_stock_books = [item.book.id for item in low_stock_items]
    out_of_stock_books = [item.book.id for item in out_of_stock_items]
    
    pending_offers_low = StockOffer.objects.filter(
        book_id__in=low_stock_books,
        status__in=['pending', 'approved']
    ).select_related('vendor', 'book')
    
    pending_offers_out = StockOffer.objects.filter(
        book_id__in=out_of_stock_books,
        status__in=['pending', 'approved']
    ).select_related('vendor', 'book')
    
    context = {
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'pending_offers_low': pending_offers_low,
        'pending_offers_out': pending_offers_out,
    }
    
    return render(request, 'warehouse/low_stock_report.html', context)