# admin_dashboard/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Q, F, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from books.models import Book, Category, SubCategory, Author, Publisher
from orders.models import Order, OrderItem
from warehouse.models import Stock, StockMovement
from vendors.models import VendorProfile, StockOffer
from accounts.models import CustomUser
from reviews.models import Review
from coupons.models import Coupon, CouponUsage
from delivery.models import Delivery, DeliveryPartner


def is_admin_or_staff(user):
    return user.is_staff or user.user_type in ['admin', 'staff']


@login_required
@user_passes_test(is_admin_or_staff)
def dashboard_home(request):
    """Main dashboard with key metrics and charts"""
    
    # Get date ranges
    today = timezone.now().date()
    current_month = today.replace(day=1)
    last_month = current_month - timedelta(days=1)
    last_month = last_month.replace(day=1)
    
    # Key Metrics
    total_books = Book.objects.filter(status='available').count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Monthly revenue
    current_month_revenue = Order.objects.filter(
        payment_status='paid',
        created_at__gte=current_month
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    last_month_revenue = Order.objects.filter(
        payment_status='paid',
        created_at__gte=last_month,
        created_at__lt=current_month
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Calculate growth percentage
    revenue_growth = 0
    if last_month_revenue > 0:
        revenue_growth = ((current_month_revenue - last_month_revenue) / last_month_revenue) * 100
    
    # Monthly orders
    current_month_orders = Order.objects.filter(created_at__gte=current_month).count()
    last_month_orders = Order.objects.filter(
        created_at__gte=last_month,
        created_at__lt=current_month
    ).count()
    
    order_growth = 0
    if last_month_orders > 0:
        order_growth = ((current_month_orders - last_month_orders) / last_month_orders) * 100
    
    # Top 5 best-selling books
    top_books = OrderItem.objects.filter(
        order__payment_status='paid'
    ).values('book__title', 'book__price').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]
    
    # Sales by category
    category_sales = OrderItem.objects.filter(
        order__payment_status='paid'
    ).values('book__category__name').annotate(
        total_sales=Sum(F('quantity') * F('price'))
    ).order_by('-total_sales')
    
    # Vendor sales share
    vendor_sales = StockOffer.objects.filter(
        status='processed'
    ).values('vendor__business_name').annotate(
        total_sales=Sum('total_amount')
    ).order_by('-total_sales')[:10]
    
    # Stock status
    total_stock = Stock.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    out_of_stock = Stock.objects.filter(quantity=0).count()
    low_stock = Stock.objects.filter(quantity__lte=F('reorder_level')).count()
    
    # Recent orders (last 10)
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Order status distribution
    order_status_counts = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Payment status distribution  
    payment_status_counts = Order.objects.values('payment_status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_books': total_books,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'current_month_revenue': current_month_revenue,
        'revenue_growth': revenue_growth,
        'current_month_orders': current_month_orders,
        'order_growth': order_growth,
        'top_books': top_books,
        'category_sales': category_sales,
        'vendor_sales': vendor_sales,
        'total_stock': total_stock,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'recent_orders': recent_orders,
        'order_status_counts': order_status_counts,
        'payment_status_counts': payment_status_counts,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def products_list(request):
    """Products management page with pagination"""
    
    # Get filter parameters
    category_filter = request.GET.get('category')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    # Base queryset
    books = Book.objects.select_related('category', 'subcategory', 'stock').prefetch_related('authors')
    
    # Apply filters
    if category_filter:
        books = books.filter(category__slug=category_filter)
    
    if status_filter:
        books = books.filter(status=status_filter)
    
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(authors__name__icontains=search_query) |
            Q(isbn__icontains=search_query)
        ).distinct()
    
    # Order by creation date
    books = books.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)  # 20 books per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = Category.objects.filter(is_active=True)
    
    # Get stock statistics
    total_products = Book.objects.count()
    in_stock_products = Stock.objects.filter(quantity__gt=0).count()
    out_of_stock_products = Stock.objects.filter(quantity=0).count()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_filter,
        'current_status': status_filter,
        'search_query': search_query,
        'total_products': total_products,
        'in_stock_products': in_stock_products,
        'out_of_stock_products': out_of_stock_products,
    }
    
    return render(request, 'admin_dashboard/products_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def categories_list(request):
    """Categories management page"""
    
    categories = Category.objects.prefetch_related('subcategories').annotate(
        book_count=Count('books'),
        total_stock=Sum('books__stock__quantity')
    ).order_by('name')
    
    # Pagination
    paginator = Paginator(categories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'admin_dashboard/categories_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_products(request, category_slug):
    """Products in a specific category"""
    
    category = get_object_or_404(Category, slug=category_slug)
    subcategory_filter = request.GET.get('subcategory')
    
    books = Book.objects.filter(category=category).select_related('subcategory', 'stock')
    
    if subcategory_filter:
        books = books.filter(subcategory__slug=subcategory_filter)
    
    books = books.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(books, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get subcategories for this category
    subcategories = SubCategory.objects.filter(category=category, is_active=True)
    
    context = {
        'category': category,
        'subcategories': subcategories,
        'page_obj': page_obj,
        'current_subcategory': subcategory_filter,
    }
    
    return render(request, 'admin_dashboard/category_products.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def warehouse_dashboard(request):
    """Warehouse management dashboard"""
    
    # Stock statistics
    total_products = Stock.objects.count()
    total_stock_quantity = Stock.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    out_of_stock = Stock.objects.filter(quantity=0).count()
    low_stock = Stock.objects.filter(quantity__lte=F('reorder_level')).count()
    
    # Recent stock movements
    recent_movements = StockMovement.objects.select_related(
        'stock__book', 'performed_by'
    ).order_by('-created_at')[:10]
    
    # Books needing reorder
    reorder_books = Stock.objects.filter(
        quantity__lte=F('reorder_level')
    ).select_related('book').order_by('quantity')[:20]
    
    # Top categories by stock value
    category_stock_value = Stock.objects.values(
        'book__category__name'
    ).annotate(
        total_value=Sum(F('quantity') * F('book__price')),
        total_quantity=Sum('quantity')
    ).order_by('-total_value')[:10]
    
    context = {
        'total_products': total_products,
        'total_stock_quantity': total_stock_quantity,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'recent_movements': recent_movements,
        'reorder_books': reorder_books,
        'category_stock_value': category_stock_value,
    }
    
    return render(request, 'admin_dashboard/warehouse_dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def orders_list(request):
    """Orders management page"""
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    payment_status_filter = request.GET.get('payment_status')
    search_query = request.GET.get('search')
    
    # Base queryset
    orders = Order.objects.select_related('user').prefetch_related('items__book')
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(billing_email__icontains=search_query)
        )
    
    orders = orders.order_by('-created_at')
    
    # Order statistics for cards
    order_stats = {
        'pending': Order.objects.filter(status='pending').count(),
        'confirmed': Order.objects.filter(status='confirmed').count(),
        'shipped': Order.objects.filter(status='shipped').count(),
        'delivered': Order.objects.filter(status='delivered').count(),
        'cancelled': Order.objects.filter(status='cancelled').count(),
        'returned': Order.objects.filter(status='returned').count(),
        'refunded': Order.objects.filter(payment_status='refunded').count(),
        'pending_payment': Order.objects.filter(payment_status='pending').count(),
    }
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'order_stats': order_stats,
        'current_status': status_filter,
        'current_payment_status': payment_status_filter,
        'search_query': search_query,
        'ORDER_STATUS': Order.ORDER_STATUS,
        'PAYMENT_STATUS': Order.PAYMENT_STATUS,
    }
    
    return render(request, 'admin_dashboard/orders_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def vendors_list(request):
    """Vendors management page"""
    
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    vendors = VendorProfile.objects.select_related('user')
    
    if status_filter:
        vendors = vendors.filter(status=status_filter)
    
    if search_query:
        vendors = vendors.filter(
            Q(business_name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    vendors = vendors.order_by('-created_at')
    
    # Vendor statistics
    vendor_stats = {
        'total': VendorProfile.objects.count(),
        'approved': VendorProfile.objects.filter(status='approved').count(),
        'pending': VendorProfile.objects.filter(status='pending').count(),
        'suspended': VendorProfile.objects.filter(status='suspended').count(),
        'rejected': VendorProfile.objects.filter(status='rejected').count(),
    }
    
    # Pagination
    paginator = Paginator(vendors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'vendor_stats': vendor_stats,
        'current_status': status_filter,
        'search_query': search_query,
        'VENDOR_STATUS': VendorProfile.VENDOR_STATUS,
    }
    
    return render(request, 'admin_dashboard/vendors_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def coupons_list(request):
    """Coupons management page"""
    
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search')
    
    coupons = Coupon.objects.all()
    
    if status_filter == 'active':
        coupons = coupons.filter(is_active=True, valid_to__gte=timezone.now())
    elif status_filter == 'expired':
        coupons = coupons.filter(valid_to__lt=timezone.now())
    elif status_filter == 'inactive':
        coupons = coupons.filter(is_active=False)
    
    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query)
        )
    
    coupons = coupons.order_by('-created_at')
    
    # Coupon statistics
    coupon_stats = {
        'total': Coupon.objects.count(),
        'active': Coupon.objects.filter(is_active=True, valid_to__gte=timezone.now()).count(),
        'expired': Coupon.objects.filter(valid_to__lt=timezone.now()).count(),
        'used_this_month': CouponUsage.objects.filter(
            used_at__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    # Pagination
    paginator = Paginator(coupons, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'coupon_stats': coupon_stats,
        'current_status': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_dashboard/coupons_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def dashboard_api_data(request):
    """API endpoint for dashboard charts data"""
    
    data_type = request.GET.get('type')
    
    if data_type == 'monthly_revenue':
        # Last 12 months revenue data
        months_data = []
        for i in range(11, -1, -1):
            month_date = timezone.now().replace(day=1) - timedelta(days=i*30)
            month_start = month_date.replace(day=1)
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
            
            revenue = Order.objects.filter(
                payment_status='paid',
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            
            months_data.append({
                'month': month_start.strftime('%b %Y'),
                'revenue': float(revenue)
            })
        
        return JsonResponse({'data': months_data})
    
    elif data_type == 'category_sales':
        # Category sales pie chart data
        category_data = OrderItem.objects.filter(
            order__payment_status='paid'
        ).values('book__category__name').annotate(
            sales=Sum(F('quantity') * F('price'))
        ).order_by('-sales')[:8]
        
        return JsonResponse({'data': list(category_data)})
    
    return JsonResponse({'error': 'Invalid data type'})