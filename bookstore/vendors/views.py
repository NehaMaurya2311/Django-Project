# vendors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import VendorProfile, StockOffer, VendorTicket, OfferStatusNotification
from .forms import VendorRegistrationForm, StockOfferForm, VendorTicketForm
# DeliveryScheduleForm
from django.utils import timezone
from logistics.models import DeliverySchedule, LogisticsPartner, PickupTracking, VendorPickup
from django.conf import settings

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
            
            messages.success(request, 'Stock offer submitted successfully!')
            return redirect('vendors:stock_offers')
    else:
        form = StockOfferForm()
    
    return render(request, 'vendors/submit_offer.html', {'form': form})

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