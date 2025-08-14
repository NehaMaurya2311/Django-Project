# vendors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import VendorProfile, StockOffer, VendorTicket, OfferStatusNotification
from django.utils import timezone
from logistics.models import DeliverySchedule, LogisticsPartner, PickupTracking, VendorPickup
from warehouse.models import Stock  
from django.conf import settings
from django.db.models import Sum, Count, Q, Avg, F, Case, When, IntegerField, Max
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .forms import (VendorRegistrationForm, StockOfferForm, VendorTicketForm, 
                   MultipleStockOfferForm, CategoryBulkOfferForm)
from books.models import Book, Category
import json
from django.views.decorators.http import require_http_methods


User = get_user_model()


def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']


# Create a combined form for vendor registration
class VendorUserCreationForm(UserCreationForm):
    """Combined form for creating user account and vendor profile"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Add styling classes
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

def vendor_register(request):
    """Combined vendor user and profile registration"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'vendor_profile'):
            return redirect('vendors:dashboard')
    
    if request.method == 'POST':
        user_form = VendorUserCreationForm(request.POST)
        vendor_form = VendorRegistrationForm(request.POST, request.FILES)
        
        if user_form.is_valid() and vendor_form.is_valid():
            try:
                with transaction.atomic():
                    # Create user account
                    user = user_form.save(commit=False)
                    user.user_type = 'vendor'
                    user.save()
                    
                    # Create vendor profile
                    vendor_profile = vendor_form.save(commit=False)
                    vendor_profile.user = user
                    vendor_profile.save()
                    
                    # Log the user in
                    login(request, user)
                    
                    messages.success(request, 'Vendor account created successfully! Your application is under review.')
                    return redirect('vendors:dashboard')
                    
            except Exception as e:
                messages.error(request, 'There was an error creating your account. Please try again.')
        else:
            # Display form errors
            for form in [user_form, vendor_form]:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        user_form = VendorUserCreationForm()
        vendor_form = VendorRegistrationForm()
    
    return render(request, 'vendors/register.html', {
        'user_form': user_form,
        'vendor_form': vendor_form
    })

@login_required
def vendor_dashboard(request):
    try:
        vendor_profile = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('vendors:register')
    
    # Statistics
    total_offers = StockOffer.objects.filter(vendor=vendor_profile).count()
    pending_offers = StockOffer.objects.filter(vendor=vendor_profile, status='pending').count()
    approved_offers = StockOffer.objects.filter(vendor=vendor_profile, status='approved').count()
    processed_offers = StockOffer.objects.filter(vendor=vendor_profile, status='processed').count()
    
    # Recent offers with enhanced status info
    recent_offers = StockOffer.objects.filter(vendor=vendor_profile).order_by('-created_at')[:5]
    
    # Delivery schedules
    active_deliveries = DeliverySchedule.objects.filter(
        vendor=vendor_profile,
        status__in=['scheduled', 'confirmed', 'pickup_assigned', 'collected', 'in_transit']
    ).count()
    
    completed_deliveries = DeliverySchedule.objects.filter(
        vendor=vendor_profile,
        status='completed'
    ).count()
    
    # Unread notifications
    unread_notifications = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile,
        is_read=False
    ).count()
    
    # Recent notifications
    recent_notifications = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile
    ).order_by('-created_at')[:5]
    
    # Open tickets
    open_tickets = VendorTicket.objects.filter(
        vendor=vendor_profile, 
        status__in=['open', 'in_progress']
    ).count()
    
    context = {
        'vendor_profile': vendor_profile,
        'total_offers': total_offers,
        'pending_offers': pending_offers,
        'approved_offers': approved_offers,
        'processed_offers': processed_offers,
        'recent_offers': recent_offers,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        'open_tickets': open_tickets,
    }
    
    return render(request, 'vendors/dashboard.html', context)


@login_required
def stock_offers_list(request):
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    offers_list = StockOffer.objects.filter(vendor=vendor_profile).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        offers_list = offers_list.filter(status=status_filter)
    
    paginator = Paginator(offers_list, 10)
    page_number = request.GET.get('page')
    offers = paginator.get_page(page_number)
    
    return render(request, 'vendors/stock_offers.html', {'offers': offers})

@login_required
def submit_stock_offer(request):
    """Enhanced stock offer submission with warehouse integration"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if vendor_profile.status != 'approved':
        messages.error(request, 'Your vendor account needs to be approved before you can submit stock offers.')
        return redirect('vendors:dashboard')
    
    if request.method == 'POST':
        form = StockOfferForm(request.POST)
        if form.is_valid():
            stock_offer = form.save(commit=False)
            stock_offer.vendor = vendor_profile
            stock_offer.save()
            
            messages.success(
                request, 
                f'Stock offer submitted successfully for "{stock_offer.book.title}"! '
                f'Quantity: {stock_offer.quantity}, Value: ₹{stock_offer.total_amount}'
            )
            return redirect('vendors:stock_offers')
    else:
        form = StockOfferForm()
    
    # Get warehouse statistics for prioritization
    warehouse_stats = get_warehouse_priority_stats()
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
        'warehouse_stats': warehouse_stats,
    }
    
    return render(request, 'vendors/submit_offer.html', context)

@login_required
def vendor_tickets(request):
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    tickets_list = VendorTicket.objects.filter(vendor=vendor_profile).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        tickets_list = tickets_list.filter(status=status_filter)
    
    paginator = Paginator(tickets_list, 10)
    page_number = request.GET.get('page')
    tickets = paginator.get_page(page_number)
    
    return render(request, 'vendors/tickets.html', {'tickets': tickets})

@login_required
def create_ticket(request):
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if request.method == 'POST':
        form = VendorTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.vendor = vendor_profile
            ticket.save()
            
            messages.success(request, f'Ticket #{ticket.ticket_id} created successfully!')
            return redirect('vendors:tickets')
    else:
        form = VendorTicketForm()
    
    return render(request, 'vendors/create_ticket.html', {'form': form})

@login_required
def ticket_detail(request, ticket_id):
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    ticket = get_object_or_404(VendorTicket, ticket_id=ticket_id, vendor=vendor_profile)
    
    return render(request, 'vendors/ticket_detail.html', {'ticket': ticket})

@login_required
def vendor_notifications(request):
    """View all notifications for vendor"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    notifications_list = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile
    ).select_related('stock_offer').order_by('-created_at')
    
    # Mark all as read when viewing
    notifications_list.filter(is_read=False).update(is_read=True)
    
    paginator = Paginator(notifications_list, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)
    
    return render(request, 'vendors/notifications.html', {'notifications': notifications})






@login_required
def schedule_delivery(request, offer_id):
    """Vendor schedules delivery for approved offer"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    offer = get_object_or_404(StockOffer, id=offer_id, vendor=vendor_profile)
    
    if offer.status != 'approved':
        messages.error(request, 'This offer cannot be scheduled for delivery.')
        return redirect('vendors:dashboard')
    
    # Check if delivery already scheduled
    if hasattr(offer, 'delivery_schedule'):
        messages.info(request, 'Delivery is already scheduled for this offer.')
        return redirect('vendors:track_delivery', offer_id=offer_id)
    
    if request.method == 'POST':
        form = DeliveryScheduleForm(request.POST)
        if form.is_valid():
            delivery = form.save(commit=False)
            delivery.stock_offer = offer
            delivery.vendor = vendor_profile
            delivery.save()
            
            # Update offer status
            offer.status = 'delivery_scheduled'
            offer.save()
            
            # Create logistics pickup record
            pickup = VendorPickup.objects.create(
                stock_offer=offer,
                vendor=vendor_profile,
                pickup_address=delivery.pickup_address,
                warehouse_address=getattr(settings, 'WAREHOUSE_ADDRESS', 'Main Warehouse'),
                scheduled_date=delivery.scheduled_delivery_date
            )
            
            # Create notification
            OfferStatusNotification.objects.create(
                stock_offer=offer,
                status='pickup_scheduled',
                message=f"Delivery scheduled for {delivery.scheduled_delivery_date.strftime('%B %d, %Y at %I:%M %p')}. Pickup ID: #{pickup.id}"
            )
            
            messages.success(request, 'Delivery scheduled successfully! You will be notified when a logistics partner is assigned.')
            return redirect('vendors:track_delivery', offer_id=offer_id)
    else:
        # Pre-fill some data
        initial_data = {
            'contact_person': vendor_profile.contact_person,
            'contact_phone': vendor_profile.phone,
            'pickup_address': vendor_profile.business_address,
        }
        form = DeliveryScheduleForm(initial=initial_data)
    
    context = {
        'form': form, 
        'offer': offer,
        'vendor_profile': vendor_profile,
    }
    
    return render(request, 'vendors/schedule_delivery.html', context)

@login_required
def track_delivery(request, offer_id):
    """Track delivery status for a specific offer"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    offer = get_object_or_404(StockOffer, id=offer_id, vendor=vendor_profile)
    
    try:
        delivery = offer.delivery_schedule
        tracking_updates = delivery.tracking_updates.all().order_by('-timestamp')
    except DeliverySchedule.DoesNotExist:
        messages.error(request, 'No delivery scheduled for this offer.')
        return redirect('vendors:dashboard')
    
    context = {
        'offer': offer,
        'delivery': delivery,
        'tracking_updates': tracking_updates,
    }
    
    return render(request, 'vendors/track_delivery.html', context)

@login_required
def delivery_history(request):
    """View all delivery history for vendor"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    deliveries_list = DeliverySchedule.objects.filter(
        vendor=vendor_profile
    ).select_related('stock_offer__book').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries_list = deliveries_list.filter(status=status_filter)
    
    paginator = Paginator(deliveries_list, 10)
    page_number = request.GET.get('page')
    deliveries = paginator.get_page(page_number)
    
    context = {
        'deliveries': deliveries,
        'status_filter': status_filter,
    }
    
    return render(request, 'vendors/delivery_history.html', context)

@login_required
def offers_awaiting_delivery(request):
    """Show approved offers that need delivery scheduling"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    # Offers that are approved but don't have delivery scheduled
    pending_offers = StockOffer.objects.filter(
        vendor=vendor_profile,
        status='approved'
    ).exclude(
        id__in=DeliverySchedule.objects.values_list('stock_offer_id', flat=True)
    ).select_related('book')
    
    context = {
        'pending_offers': pending_offers,
    }
    
    return render(request, 'vendors/offers_awaiting_delivery.html', context)

# ADMIN/STAFF VIEWS FOR MANAGING OFFERS

@login_required
@user_passes_test(is_staff_or_admin)
def approve_stock_offer(request, offer_id):
    """Staff/Admin approves stock offer"""
    offer = get_object_or_404(StockOffer, id=offer_id)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        
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
            message=f"Great news! Your offer for '{offer.book.title}' ({offer.quantity} copies) has been approved. Please schedule delivery as soon as possible."
        )
        
        messages.success(request, f'Offer approved! Vendor {offer.vendor.business_name} will be notified to schedule delivery.')
        
    return redirect('admin:vendors_stockoffer_changelist')

@login_required
@user_passes_test(is_staff_or_admin)
def reject_stock_offer(request, offer_id):
    """Staff/Admin rejects stock offer"""
    offer = get_object_or_404(StockOffer, id=offer_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        offer.status = 'rejected'
        offer.reviewed_by = request.user
        offer.reviewed_at = timezone.now()
        if rejection_reason:
            offer.admin_notes = rejection_reason
        offer.save()
        
        # Create notification for vendor
        OfferStatusNotification.objects.create(
            stock_offer=offer,
            status='rejected',
            message=f"Your offer for '{offer.book.title}' was not accepted. Reason: {rejection_reason}"
        )
        
        messages.success(request, f'Offer rejected. Vendor {offer.vendor.business_name} has been notified.')
        
    return redirect('admin:vendors_stockoffer_changelist')


@login_required
def book_search_api(request):
    """FIXED API endpoint for searching books with warehouse priority"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'books': []})
    
    try:
        # Search books with warehouse stock information
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(authors__name__icontains=query),
            status='available'
        ).select_related('category').prefetch_related('authors').distinct()[:20]
        
        book_list = []
        for book in books:
            authors = ', '.join([author.name for author in book.authors.all()])
            
            # Get warehouse stock info
            try:
                stock = Stock.objects.get(book=book)
                current_stock = stock.available_quantity
                reorder_level = stock.reorder_level
                
                if stock.available_quantity == 0:
                    stock_status = 'out_of_stock'
                    priority_level = 'high'
                elif stock.available_quantity <= stock.reorder_level:
                    stock_status = 'low_stock'
                    priority_level = 'medium'
                else:
                    stock_status = 'in_stock'
                    priority_level = 'normal'
                    
            except Stock.DoesNotExist:
                stock_status = 'no_stock_record'
                current_stock = 0
                reorder_level = 10
                priority_level = 'high'
            
            # Check existing vendor offers
            existing_offers = StockOffer.objects.filter(
                vendor=vendor_profile,
                book=book,
                status__in=['pending', 'approved']
            ).aggregate(
                total_pending=Sum('quantity', filter=Q(status='pending')),
                total_approved=Sum('quantity', filter=Q(status='approved'))
            )
            
            # Calculate suggested quantity
            suggested_qty = calculate_suggested_quantity(book)
            
            book_list.append({
                'id': book.id,
                'title': book.title,
                'authors': authors,
                'isbn': book.isbn,
                'category': book.category.name,
                'stock_status': stock_status,
                'current_stock': current_stock,
                'priority_level': priority_level,
                'existing_pending': existing_offers['total_pending'] or 0,
                'existing_approved': existing_offers['total_approved'] or 0,
                'reorder_level': reorder_level,
                'suggested_quantity': suggested_qty,
            })
        
        # Sort by priority (high priority first)
        priority_order = {'high': 0, 'medium': 1, 'normal': 2}
        book_list.sort(key=lambda x: priority_order.get(x['priority_level'], 3))
        
        return JsonResponse({'books': book_list})
        
    except Exception as e:
        return JsonResponse({'error': f'Search error: {str(e)}'}, status=500)


@login_required
def category_books_api(request):
    """FIXED API endpoint for books in a category with warehouse awareness"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'error': 'Category ID is required'}, status=400)
    
    try:
        category = Category.objects.get(id=category_id)
        vendor_profile = get_object_or_404(VendorProfile, user=request.user)
        
        # Get books in this category
        books = Book.objects.filter(
            category=category,
            status='available'
        ).select_related('category').prefetch_related('authors')
        
        book_list = []
        priority_counts = {'high': 0, 'medium': 0, 'normal': 0}
        
        for book in books:
            authors = ', '.join([author.name for author in book.authors.all()])
            
            # Get stock information
            try:
                stock = Stock.objects.get(book=book)
                current_stock = stock.available_quantity
                reserved_stock = stock.reserved_quantity
                reorder_level = stock.reorder_level
                
                if current_stock == 0:
                    stock_status = 'out_of_stock'
                    priority = 'high'
                elif current_stock <= reorder_level:
                    stock_status = 'low_stock'
                    priority = 'medium'
                else:
                    stock_status = 'in_stock'
                    priority = 'normal'
                    
            except Stock.DoesNotExist:
                stock_status = 'no_stock_record'
                current_stock = 0
                reserved_stock = 0
                reorder_level = 10
                priority = 'high'
            
            priority_counts[priority] += 1
            
            # Check vendor's existing offers
            existing_offers = StockOffer.objects.filter(
                vendor=vendor_profile,
                book=book
            ).aggregate(
                pending_quantity=Sum('quantity', filter=Q(status='pending')),
                approved_quantity=Sum('quantity', filter=Q(status='approved')),
                total_offers=Count('id'),
                latest_offer_date=Max('created_at')
            )
            
            # Calculate suggested quantity
            suggested_qty = calculate_suggested_quantity(book)
            
            book_list.append({
                'id': book.id,
                'title': book.title,
                'authors': authors,
                'isbn': book.isbn,
                'current_stock': current_stock,
                'reserved_stock': reserved_stock,
                'reorder_level': reorder_level,
                'stock_status': stock_status,
                'priority': priority,
                'suggested_quantity': suggested_qty,
                'existing_pending': existing_offers['pending_quantity'] or 0,
                'existing_approved': existing_offers['approved_quantity'] or 0,
                'has_existing_offers': existing_offers['total_offers'] > 0,
                'last_offer_date': existing_offers['latest_offer_date'].isoformat() if existing_offers['latest_offer_date'] else None
            })
        
        # Sort by priority (high need first)
        priority_order = {'high': 0, 'medium': 1, 'normal': 2}
        book_list.sort(key=lambda x: (priority_order.get(x['priority'], 3), x['title']))
        
        return JsonResponse({
            'books': book_list,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug
            },
            'summary': {
                'total_books': len(book_list),
                'high_priority': priority_counts['high'],
                'medium_priority': priority_counts['medium'],
                'normal_priority': priority_counts['normal'],
            }
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error loading category books: {str(e)}'}, status=500)


@login_required
def categories_api(request):
    """FIXED API endpoint for categories with warehouse-aware statistics"""
    try:
        # Get categories with book counts
        categories = Category.objects.filter(
            is_active=True,
            books__status='available'
        ).distinct().annotate(
            total_books=Count('books', filter=Q(books__status='available'))
        ).filter(total_books__gt=0)
        
        category_list = []
        for category in categories:
            # Get stock statistics for books in this category
            category_books = Book.objects.filter(
                category=category, 
                status='available'
            )
            
            # Count books by stock status
            out_of_stock = 0
            low_stock = 0
            in_stock = 0
            no_stock_record = 0
            
            for book in category_books:
                try:
                    stock = Stock.objects.get(book=book)
                    if stock.available_quantity == 0:
                        out_of_stock += 1
                    elif stock.available_quantity <= stock.reorder_level:
                        low_stock += 1
                    else:
                        in_stock += 1
                except Stock.DoesNotExist:
                    no_stock_record += 1
            
            # Calculate priority
            needs_attention = out_of_stock + low_stock + no_stock_record
            if needs_attention > 10:
                priority = 'high'
            elif needs_attention > 5:
                priority = 'medium'
            else:
                priority = 'normal'
            
            category_list.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'total_books': category.total_books,
                'out_of_stock_books': out_of_stock,
                'low_stock_books': low_stock,
                'in_stock_books': in_stock,
                'no_stock_record': no_stock_record,
                'needs_attention': needs_attention,
                'priority': priority,
                'opportunity_score': int((needs_attention / category.total_books) * 100) if category.total_books > 0 else 0
            })
        
        # Sort by priority and needs attention
        category_list.sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1 if x['priority'] == 'medium' else 2,
            -x['needs_attention']
        ))
        
        return JsonResponse({'categories': category_list})
        
    except Exception as e:
        return JsonResponse({'error': f'Categories error: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def submit_multiple_offer(request):
    """Handle multiple book offers in one submission - FIXED VERSION"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if vendor_profile.status != 'approved':
        return JsonResponse({'success': False, 'message': 'Your vendor account needs to be approved.'})
    
    try:
        # Parse the JSON data properly
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            books_data = json.loads(data.get('books_data', '[]'))
            availability_date = data.get('availability_date')
            expiry_date = data.get('expiry_date')
            notes = data.get('notes', '')
        else:
            # Fallback for form data
            books_data = json.loads(request.POST.get('books_data', '[]'))
            availability_date = request.POST.get('availability_date')
            expiry_date = request.POST.get('expiry_date')
            notes = request.POST.get('notes', '')
        
        if not books_data:
            return JsonResponse({'success': False, 'message': 'No books selected for offer.'})
        
        if not availability_date or not expiry_date:
            return JsonResponse({'success': False, 'message': 'Please provide availability and expiry dates.'})
        
        created_offers = []
        total_value = 0
        
        with transaction.atomic():
            for book_data in books_data:
                try:
                    book = Book.objects.get(id=book_data['id'])
                    quantity = int(book_data['quantity'])
                    unit_price = float(book_data['price'])
                    
                    if quantity <= 0 or unit_price <= 0:
                        return JsonResponse({'success': False, 'message': f'Invalid quantity or price for book: {book.title}'})
                    
                    offer = StockOffer.objects.create(
                        vendor=vendor_profile,
                        book=book,
                        quantity=quantity,
                        unit_price=unit_price,
                        availability_date=availability_date,
                        expiry_date=expiry_date,
                        notes=f"{notes}\n[Multi-book offer batch]".strip()
                    )
                    created_offers.append(offer)
                    total_value += offer.total_amount
                    
                except Book.DoesNotExist:
                    return JsonResponse({'success': False, 'message': f'Book with ID {book_data["id"]} not found.'})
                except (ValueError, KeyError) as e:
                    return JsonResponse({'success': False, 'message': f'Invalid data format: {str(e)}'})
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully submitted {len(created_offers)} book offers! Total value: ₹{total_value:,.2f}',
            'offers_count': len(created_offers),
            'total_value': total_value
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data provided.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error submitting offers: {str(e)}'})
    

@login_required
def submit_category_bulk_offer(request):
    """Enhanced category bulk offer with real warehouse data"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if vendor_profile.status != 'approved':
        messages.error(request, 'Your vendor account needs to be approved.')
        return redirect('vendors:dashboard')
    
    if request.method == 'POST':
        form = CategoryBulkOfferForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            default_quantity = form.cleaned_data['default_quantity']
            default_price = form.cleaned_data['default_price']
            availability_date = form.cleaned_data['availability_date']
            expiry_date = form.cleaned_data['expiry_date']
            notes = form.cleaned_data['notes']
            
            # Get books that need restocking and don't have pending offers
            books_needing_stock = Book.objects.filter(
                category=category,
                status='available'
            ).annotate(
                needs_restock=Case(
                    When(stock__isnull=True, then=1),  # No stock record
                    When(stock__quantity=0, then=1),   # Out of stock
                    When(stock__quantity__lte=F('stock__reorder_level'), then=1),  # Low stock
                    default=0,
                    output_field=IntegerField()
                )
            ).filter(needs_restock=1).exclude(
                stockoffer__vendor=vendor_profile,
                stockoffer__status__in=['pending', 'approved']
            )
            
            if not books_needing_stock.exists():
                messages.warning(
                    request,
                    f'No books in "{category.name}" need restocking or all already have pending offers.'
                )
                return redirect('vendors:submit_category_bulk_offer')
            
            created_offers = []
            total_value = 0
            
            try:
                with transaction.atomic():
                    for book in books_needing_stock:
                        # Use smart quantity calculation
                        smart_quantity = calculate_suggested_quantity(book)
                        final_quantity = max(default_quantity, smart_quantity)
                        
                        offer = StockOffer.objects.create(
                            vendor=vendor_profile,
                            book=book,
                            quantity=final_quantity,
                            unit_price=default_price,
                            availability_date=availability_date,
                            expiry_date=expiry_date,
                            notes=f"{notes}\n[Bulk category offer: {category.name}]\n[Smart quantity: {smart_quantity}]".strip()
                        )
                        created_offers.append(offer)
                        total_value += offer.total_amount
                
                messages.success(
                    request,
                    f'Created {len(created_offers)} offers for "{category.name}" books that need restocking! '
                    f'Total value: ₹{total_value:,.2f}'
                )
                return redirect('vendors:stock_offers')
                
            except Exception as e:
                messages.error(request, f'Error creating bulk offers: {str(e)}')
    else:
        form = CategoryBulkOfferForm()
    
    # Get priority categories
    priority_categories = get_priority_categories_for_vendor(vendor_profile)
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
        'priority_categories': priority_categories,
    }
    
    return render(request, 'vendors/submit_category_bulk_offer.html', context)


# Helper Functions
def calculate_suggested_quantity(book):
    """Calculate smart suggested quantity based on stock levels"""
    try:
        stock = Stock.objects.get(book=book)
        reorder_level = stock.reorder_level
        current_stock = stock.available_quantity
        
        if current_stock == 0:
            # Out of stock - suggest reorder level + buffer
            return reorder_level + 10
        elif current_stock <= reorder_level:
            # Low stock - suggest to reach comfortable level
            return max(reorder_level - current_stock + 5, 5)
        else:
            # In stock - minimal quantity
            return 5
            
    except Stock.DoesNotExist:
        # No stock record - suggest default
        return 15

def get_warehouse_priority_stats():
    """Get warehouse statistics to show priority areas"""
    try:
        return {
            'out_of_stock_books': Stock.objects.filter(available_quantity=0).count(),
            'low_stock_books': Stock.objects.filter(
                available_quantity__lte=F('reorder_level'),
                available_quantity__gt=0
            ).count(),
            'total_books_need_restock': Stock.objects.filter(
                Q(available_quantity=0) | Q(available_quantity__lte=F('reorder_level'))
            ).count(),
            'categories_need_attention': Category.objects.filter(
                books__stock__available_quantity__lte=F('books__stock__reorder_level'),
                is_active=True
            ).distinct().count()
        }
    except Exception:
        return {
            'out_of_stock_books': 0,
            'low_stock_books': 0,
            'total_books_need_restock': 0,
            'categories_need_attention': 0
        }

def calculate_category_opportunity(category):
    """Calculate opportunity score for a category"""
    needs_attention = category.out_of_stock_books + category.low_stock_books + category.no_stock_record
    total_books = category.total_books
    
    if total_books == 0:
        return 0
        
    return int((needs_attention / total_books) * 100)

def get_priority_categories_for_vendor(vendor_profile):
    """Get categories prioritized for this vendor"""
    return Category.objects.filter(
        is_active=True,
        books__status='available'
    ).annotate(
        needs_restock=Count('books', filter=Q(
            books__stock__quantity__lte=F('books__stock__reorder_level')
        ) | Q(books__stock__isnull=True)),
        total_books=Count('books', filter=Q(books__status='available')),
        vendor_recent_offers=Count('books__stockoffer', filter=Q(
            books__stockoffer__vendor=vendor_profile,
            books__stockoffer__created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ))
    ).filter(
        needs_restock__gt=0
    ).order_by('-needs_restock', 'name')