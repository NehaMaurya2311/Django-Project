# vendors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from logistics.models import DeliverySchedule, LogisticsPartner, DeliveryTracking
from warehouse.models import Stock  
from django.conf import settings
from django.db.models import Sum, Count, Q, Avg, F, Case, When, IntegerField, Max
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .forms import (VendorRegistrationForm, StockOfferForm, VendorTicketForm,  MultipleStockOfferForm, CategoryBulkOfferForm, DeliveryScheduleForm, QuickVendorLocationForm, VendorUserCreationForm)
from books.models import Book, Category
import json
from django.views.decorators.http import require_http_methods
from .models import VendorProfile, StockOffer, VendorTicket, OfferStatusNotification
from logistics.models import VendorLocation, DeliverySchedule, LogisticsPartner, DeliveryTracking

User = get_user_model()


def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

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
    """FIXED: Dashboard with proper out-of-stock book alerts"""
    try:
        vendor_profile = request.user.vendor_profile
    except VendorProfile.DoesNotExist:
        return redirect('vendors:register')

    # Statistics
    total_offers = StockOffer.objects.filter(vendor=vendor_profile).count()
    pending_offers = StockOffer.objects.filter(vendor=vendor_profile, status='pending').count()

    approved_offers_without_delivery = StockOffer.objects.filter(
        vendor=vendor_profile,
        status='approved'
    ).exclude(
        id__in=DeliverySchedule.objects.values_list('stock_offer_id', flat=True)
    ).count()

    processed_offers = StockOffer.objects.filter(vendor=vendor_profile, status='processed').count()

    # FIXED: Add warehouse opportunity alerts
    warehouse_opportunities = get_vendor_opportunities(vendor_profile)

    # Recent offers
    recent_offers = StockOffer.objects.filter(vendor=vendor_profile).order_by('-created_at')[:5]

    # Active deliveries
    # The following line is now redundant and can be removed, as the import is at the top.
    # from logistics.models import DeliverySchedule
    active_deliveries = DeliverySchedule.objects.filter(
        vendor=vendor_profile,
        status__in=['scheduled', 'confirmed', 'pickup_assigned', 'collected', 'in_transit', 'arrived']
    ).count()

    completed_deliveries = DeliverySchedule.objects.filter(
        vendor=vendor_profile,
        status='completed'
    ).count()

    # Recent notifications
    unread_notifications = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile,
        is_read=False
    ).count()

    recent_notifications = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile
    ).order_by('-created_at')[:5]

    context = {
        'vendor_profile': vendor_profile,
        'total_offers': total_offers,
        'pending_offers': pending_offers,
        'approved_offers': approved_offers_without_delivery,
        'processed_offers': processed_offers,
        'recent_offers': recent_offers,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'unread_notifications': unread_notifications,
        'recent_notifications': recent_notifications,
        # FIXED: Add warehouse opportunities
        'warehouse_opportunities': warehouse_opportunities,
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
def vendor_locations(request):
    """Manage vendor pickup locations"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if request.method == 'POST':
        form = QuickVendorLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.vendor = vendor_profile
            location.is_active = True
            location.save()
            messages.success(request, f'Location "{location.name}" added successfully!')
            return redirect('vendors:vendor_locations')
    else:
        form = QuickVendorLocationForm()
        # Pre-fill with vendor's primary address
        form.fields['address'].initial = vendor_profile.business_address
        form.fields['city'].initial = vendor_profile.city
        form.fields['state'].initial = vendor_profile.state
        form.fields['pincode'].initial = vendor_profile.pincode
        form.fields['contact_person'].initial = vendor_profile.contact_person
        form.fields['phone'].initial = vendor_profile.phone
    
    locations = VendorLocation.objects.filter(vendor=vendor_profile).order_by('-is_primary', 'name')
    
    context = {
        'form': form,
        'locations': locations,
        'vendor_profile': vendor_profile,
    }
    
    return render(request, 'vendors/vendor_locations.html', context)


@login_required
def notifications_count(request):
    """API endpoint for notification count"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    count = OfferStatusNotification.objects.filter(
        stock_offer__vendor=vendor_profile,
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})


@login_required
def bulk_schedule_delivery(request):
    """FIXED: Handle both GET and POST for bulk delivery scheduling"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    if request.method == 'GET':
        # Handle GET request - show the bulk scheduling form
        
        # Get selected offer IDs from URL parameters
        offers_param = request.GET.get('offers', '')
        selected_offer_ids = []
        
        if offers_param:
            try:
                selected_offer_ids = [id.strip() for id in offers_param.split(',') if id.strip()]
            except:
                selected_offer_ids = []
        
        # If no offers in URL, try to get from session
        if not selected_offer_ids:
            # You could also check session storage here if needed
            messages.error(request, 'No offers selected for bulk scheduling.')
            return redirect('vendors:offers_awaiting_delivery')
        
        # Validate that offers exist and belong to vendor
        valid_offers = StockOffer.objects.filter(
            id__in=selected_offer_ids,
            vendor=vendor_profile,
            status='approved'
        ).exclude(
            id__in=DeliverySchedule.objects.values_list('stock_offer_id', flat=True)
        )
        
        if not valid_offers.exists():
            messages.error(request, 'No valid offers found for bulk scheduling.')
            return redirect('vendors:offers_awaiting_delivery')
        
        # Create forms
        form = DeliveryScheduleForm(vendor=vendor_profile)
        location_form = QuickVendorLocationForm()
        
        # Pre-fill contact info
        form.fields['contact_person'].initial = vendor_profile.contact_person
        form.fields['contact_phone'].initial = vendor_profile.phone
        
        # Pre-fill location form
        location_form.fields['name'].initial = "New Location"
        location_form.fields['address'].initial = vendor_profile.business_address
        location_form.fields['city'].initial = vendor_profile.city
        location_form.fields['state'].initial = vendor_profile.state
        location_form.fields['pincode'].initial = vendor_profile.pincode
        location_form.fields['contact_person'].initial = vendor_profile.contact_person
        location_form.fields['phone'].initial = vendor_profile.phone
        
        # Get existing locations
        existing_locations = VendorLocation.objects.filter(
            vendor=vendor_profile, is_active=True
        ).order_by('-is_primary', 'name')
        
        # Create primary location if none exist
        if not existing_locations.exists():
            primary_location = VendorLocation.objects.create(
                vendor=vendor_profile,
                name="Primary Business Address",
                address=vendor_profile.business_address,
                city=vendor_profile.city,
                state=vendor_profile.state,
                pincode=vendor_profile.pincode,
                contact_person=vendor_profile.contact_person,
                phone=vendor_profile.phone,
                is_primary=True,
                is_active=True
            )
            existing_locations = VendorLocation.objects.filter(vendor=vendor_profile, is_active=True)
        
        context = {
            'form': form,
            'location_form': location_form,
            'vendor_profile': vendor_profile,
            'existing_locations': existing_locations,
            'selected_offers': valid_offers,
            'selected_offer_ids': selected_offer_ids,
        }
        
        return render(request, 'vendors/schedule_delivery.html', context)
    
    elif request.method == 'POST':
        # Handle POST request - process the bulk scheduling
        
        try:
            # Get selected offer IDs - handle both form data and JSON
            selected_offers = request.POST.getlist('selected_offers[]')
            if not selected_offers:
                selected_offers = request.POST.getlist('selected_offers')
            
            if not selected_offers:
                return JsonResponse({
                    'success': False, 
                    'message': 'No offers selected for scheduling.'
                })
            
            print(f"DEBUG: Selected offers: {selected_offers}")  # Debug log
            
            # Validate offers belong to vendor and are approved
            offers = StockOffer.objects.filter(
                id__in=selected_offers,
                vendor=vendor_profile,
                status='approved'
            ).exclude(
                id__in=DeliverySchedule.objects.values_list('stock_offer_id', flat=True)
            )
            
            if not offers.exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'No valid offers found for scheduling. Offers may already be scheduled or not approved.'
                })
            
            # Get and parse form data with proper datetime handling
            delivery_date_str = request.POST.get('scheduled_delivery_date')
            contact_person = request.POST.get('contact_person', '').strip()
            contact_phone = request.POST.get('contact_phone', '').strip()
            special_instructions = request.POST.get('special_instructions', '')
            vendor_location_id = request.POST.get('vendor_location')
            
            print(f"DEBUG: Form data - Date: {delivery_date_str}, Contact: {contact_person}, Phone: {contact_phone}, Location: {vendor_location_id}")
            
            # Validate required fields properly
            if not delivery_date_str:
                return JsonResponse({
                    'success': False, 
                    'message': 'Please select a delivery date and time.'
                })
                
            if not contact_person:
                return JsonResponse({
                    'success': False, 
                    'message': 'Please enter a contact person name.'
                })
                
            if not contact_phone:
                return JsonResponse({
                    'success': False, 
                    'message': 'Please enter a contact phone number.'
                })
            
            # Parse datetime properly with timezone support
            try:
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone as django_timezone
                
                # Parse the datetime string
                if 'T' in delivery_date_str:
                    # ISO format from datetime-local input
                    delivery_date = parse_datetime(delivery_date_str)
                    if delivery_date is None:
                        # Try parsing as naive datetime and make it timezone-aware
                        from datetime import datetime
                        delivery_date = datetime.fromisoformat(delivery_date_str.replace('T', ' '))
                        delivery_date = django_timezone.make_aware(delivery_date)
                else:
                    # Other format
                    from datetime import datetime
                    delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d %H:%M:%S')
                    delivery_date = django_timezone.make_aware(delivery_date)
                    
                # Ensure timezone awareness
                if delivery_date.tzinfo is None:
                    delivery_date = django_timezone.make_aware(delivery_date)
                    
            except (ValueError, TypeError) as e:
                print(f"DEBUG: DateTime parsing error: {e}")
                return JsonResponse({
                    'success': False, 
                    'message': f'Invalid delivery date format. Please select a valid date and time.'
                })
            
            # Handle vendor location properly
            vendor_location = None
            if vendor_location_id:
                try:
                    vendor_location = VendorLocation.objects.get(
                        id=vendor_location_id, 
                        vendor=vendor_profile,
                        is_active=True
                    )
                except VendorLocation.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Selected pickup location is not valid.'
                    })
            
            # If no location selected, create/get default location
            if not vendor_location:
                vendor_location, created = VendorLocation.objects.get_or_create(
                    vendor=vendor_profile,
                    name="Primary Business Address",
                    defaults={
                        'address': vendor_profile.business_address,
                        'city': vendor_profile.city,
                        'state': vendor_profile.state,
                        'pincode': vendor_profile.pincode,
                        'contact_person': vendor_profile.contact_person,
                        'phone': vendor_profile.phone,
                        'is_primary': True,
                        'is_active': True
                    }
                )
            
            # Create delivery schedules with proper error handling and datetime formatting
            created_deliveries = []
            total_value = 0
            
            with transaction.atomic():
                for offer in offers:
                    try:
                        # Create delivery schedule with proper datetime object
                        delivery = DeliverySchedule.objects.create(
                            stock_offer=offer,
                            vendor=vendor_profile,
                            vendor_location=vendor_location,
                            scheduled_delivery_date=delivery_date,  # Now properly parsed datetime
                            contact_person=contact_person,
                            contact_phone=contact_phone,
                            special_instructions=special_instructions,
                            status='scheduled'
                        )
                        
                        # Format datetime properly for display
                        formatted_date = delivery_date.strftime('%B %d, %Y at %I:%M %p')
                        
                        # Create tracking entry
                        DeliveryTracking.objects.create(
                            delivery=delivery,
                            status='scheduled',
                            notes=f"Bulk delivery scheduled for {formatted_date}",
                            updated_by=request.user
                        )
                        
                        # Create notification
                        OfferStatusNotification.objects.create(
                            stock_offer=offer,
                            status='pickup_scheduled',
                            message=f"Delivery scheduled for {formatted_date}. "
                                    f"Logistics partner will be assigned soon."
                        )
                        
                        created_deliveries.append(delivery)
                        total_value += offer.total_amount
                        
                    except Exception as e:
                        print(f"DEBUG: Error creating delivery for offer {offer.id}: {str(e)}")
                        raise e
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully scheduled {len(created_deliveries)} deliveries! Total value: ₹{total_value:,.2f}',
                'deliveries_count': len(created_deliveries),
                'total_value': total_value
            })
            
        except Exception as e:
            print(f"DEBUG: Bulk schedule error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False, 
                'message': f'Error scheduling deliveries: {str(e)}'
            })

@login_required
def schedule_single_delivery(request, offer_id):
    """Redirect single delivery to the main schedule delivery page"""
    return redirect('vendors:schedule_delivery', offer_id=offer_id)

@login_required
def schedule_delivery(request, offer_id):
    """FIXED: Vendor schedules delivery with proper form handling"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    offer = get_object_or_404(StockOffer, id=offer_id, vendor=vendor_profile)
    
    # Check status
    if offer.status != 'approved':
        messages.error(
            request, 
            f'This offer cannot be scheduled for delivery. Current status: {offer.get_status_display()}. '
            f'Only approved offers can be scheduled.'
        )
        return redirect('vendors:offers_awaiting_delivery')
    
    # Check if delivery already scheduled
    try:
        existing_delivery = DeliverySchedule.objects.get(stock_offer=offer)
        messages.info(
            request, 
            f'Delivery is already scheduled for this offer (ID: #{existing_delivery.id}). '
            f'Current status: {existing_delivery.get_status_display()}'
        )
        return redirect('vendors:track_delivery', offer_id=offer_id)
    except DeliverySchedule.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = DeliveryScheduleForm(request.POST, vendor=vendor_profile)
        location_form = QuickVendorLocationForm(request.POST)
        
        # FIXED: Handle new location creation separately to prevent auto-creation
        if 'create_location' in request.POST:
            if location_form.is_valid():
                location = location_form.save(commit=False)
                location.vendor = vendor_profile
                location.is_active = True
                
                # FIXED: Set as primary if requested
                if request.POST.get('set_as_primary'):
                    # Remove primary from other locations
                    VendorLocation.objects.filter(
                        vendor=vendor_profile, 
                        is_primary=True
                    ).update(is_primary=False)
                    location.is_primary = True
                
                location.save()
                messages.success(
                    request, 
                    f'New pickup location "{location.name}" added successfully!'
                )
                
                # Redirect to same page to refresh location list
                return redirect('vendors:schedule_delivery', offer_id=offer_id)
            else:
                messages.error(request, 'Please correct the errors in the location form.')
        
        # FIXED: Handle delivery scheduling (not location creation)
        elif form.is_valid():
            try:
                with transaction.atomic():
                    # Create delivery schedule
                    delivery = form.save(commit=False)
                    delivery.stock_offer = offer
                    delivery.vendor = vendor_profile
                    delivery.status = 'scheduled'
                    delivery.save()
                    
                    # Create initial tracking entry
                    DeliveryTracking.objects.create(
                        delivery=delivery,
                        status='scheduled',
                        notes=f"Delivery scheduled by vendor for {delivery.scheduled_delivery_date.strftime('%B %d, %Y at %I:%M %p')}",
                        updated_by=request.user
                    )
                    
                    # Create notification
                    OfferStatusNotification.objects.create(
                        stock_offer=offer,
                        status='pickup_scheduled',
                        message=(
                            f"Delivery scheduled for {delivery.scheduled_delivery_date.strftime('%B %d, %Y at %I:%M %p')}. "
                            f"Our logistics team will assign a partner and contact you soon."
                        )
                    )
                    
                    messages.success(
                        request, 
                        f'Delivery scheduled successfully! '
                        f'Delivery ID: #{delivery.id}. '
                        f'You will be notified when a logistics partner is assigned.'
                    )
                    return redirect('vendors:track_delivery', offer_id=offer_id)
                    
            except Exception as e:
                messages.error(
                    request, 
                    f'Error scheduling delivery: {str(e)}. Please try again.'
                )
        else:
            # Display form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
    else:
        form = DeliveryScheduleForm(vendor=vendor_profile)
        location_form = QuickVendorLocationForm()
        
        # Pre-fill contact info from vendor profile
        form.fields['contact_person'].initial = vendor_profile.contact_person
        form.fields['contact_phone'].initial = vendor_profile.phone
        
        # FIXED: Pre-fill new location form with vendor's business address
        location_form.fields['name'].initial = "New Location"
        location_form.fields['address'].initial = vendor_profile.business_address
        location_form.fields['city'].initial = vendor_profile.city
        location_form.fields['state'].initial = vendor_profile.state
        location_form.fields['pincode'].initial = vendor_profile.pincode
        location_form.fields['contact_person'].initial = vendor_profile.contact_person
        location_form.fields['phone'].initial = vendor_profile.phone
    
    # Get existing locations
    existing_locations = VendorLocation.objects.filter(
        vendor=vendor_profile, is_active=True
    ).order_by('-is_primary', 'name')
    
    # FIXED: Create primary location only if no locations exist
    if not existing_locations.exists():
        primary_location = VendorLocation.objects.create(
            vendor=vendor_profile,
            name="Primary Business Address",
            address=vendor_profile.business_address,
            city=vendor_profile.city,
            state=vendor_profile.state,
            pincode=vendor_profile.pincode,
            contact_person=vendor_profile.contact_person,
            phone=vendor_profile.phone,
            is_primary=True,
            is_active=True
        )
        existing_locations = VendorLocation.objects.filter(vendor=vendor_profile, is_active=True)
    
    context = {
        'form': form,
        'location_form': location_form,
        'offer': offer,
        'vendor_profile': vendor_profile,
        'existing_locations': existing_locations,
    }
    
    return render(request, 'vendors/schedule_delivery.html', context)

@login_required
def track_delivery(request, offer_id):
    """Track delivery status for a specific offer"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    offer = get_object_or_404(StockOffer, id=offer_id, vendor=vendor_profile)
    
    try:
        delivery = DeliverySchedule.objects.get(stock_offer=offer)
        tracking_updates = delivery.tracking_updates.all().order_by('-timestamp')
    except DeliverySchedule.DoesNotExist:
        messages.error(request, 'No delivery scheduled for this offer.')
        return redirect('vendors:dashboard')
    
    # Calculate delivery progress
    status_progression = {
        'scheduled': 10,
        'confirmed': 20,
        'pickup_assigned': 40,
        'collected': 60,
        'in_transit': 80,
        'arrived': 90,
        'verified': 95,
        'completed': 100
    }
    
    progress_percentage = status_progression.get(delivery.status, 0)
    
    context = {
        'offer': offer,
        'delivery': delivery,
        'tracking_updates': tracking_updates,
        'progress_percentage': progress_percentage,
    }
    
    return render(request, 'vendors/track_delivery.html', context)


@login_required
def delivery_history(request):
    """View all delivery history for vendor"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    deliveries_list = DeliverySchedule.objects.filter(
        vendor=vendor_profile
    ).select_related('stock_offer__book', 'assigned_partner', 'vendor_location').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries_list = deliveries_list.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        deliveries_list = deliveries_list.filter(
            Q(stock_offer__book__title__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(assigned_partner__name__icontains=search_query)
        )
    
    paginator = Paginator(deliveries_list, 10)
    page_number = request.GET.get('page')
    deliveries = paginator.get_page(page_number)
    
    # Calculate stats
    stats = {
        'total_deliveries': deliveries_list.count(),
        'pending_deliveries': deliveries_list.filter(
            status__in=['scheduled', 'confirmed', 'pickup_assigned']
        ).count(),
        'in_transit': deliveries_list.filter(
            status__in=['collected', 'in_transit']
        ).count(),
        'completed': deliveries_list.filter(status='completed').count(),
    }
    
    context = {
        'deliveries': deliveries,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': stats,
    }
    
    return render(request, 'vendors/delivery-history.html', context)


@login_required
def offers_awaiting_delivery(request):
    """FIXED: Show approved offers that need delivery scheduling"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    
    # FIXED: Only show approved offers that don't have delivery scheduled
    pending_offers = StockOffer.objects.filter(
        vendor=vendor_profile,
        status='approved'  # Only approved offers
    ).exclude(
        # Exclude offers that already have delivery schedules
        id__in=DeliverySchedule.objects.values_list('stock_offer_id', flat=True)
    ).select_related('book__category').prefetch_related('book__authors').order_by('-created_at')
    
    context = {
        'pending_offers': pending_offers,
        'vendor_profile': vendor_profile,
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
    """FIXED: API endpoint that properly shows out-of-stock books"""
    vendor_profile = get_object_or_404(VendorProfile, user=request.user)
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'books': []})
    
    try:
        # FIXED: Include out_of_stock books in search results
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(authors__name__icontains=query),
            # FIXED: Include both available AND out_of_stock books
            status__in=['available', 'out_of_stock']
        ).select_related('category').prefetch_related('authors').distinct()[:20]
        
        book_list = []
        for book in books:
            authors = ', '.join([author.name for author in book.authors.all()])
            
            # Get warehouse stock info
            try:
                stock = Stock.objects.get(book=book)
                current_stock = stock.available_quantity
                reorder_level = stock.reorder_level
                
                # FIXED: Proper stock status determination
                if stock.available_quantity == 0:
                    stock_status = 'out_of_stock'
                    priority_level = 'high'
                    priority_text = 'OUT OF STOCK - High Priority'
                elif stock.available_quantity <= stock.reorder_level:
                    stock_status = 'low_stock'
                    priority_level = 'medium'
                    priority_text = 'Low Stock - Medium Priority'
                else:
                    stock_status = 'in_stock'
                    priority_level = 'normal'
                    priority_text = 'In Stock - Normal Priority'
                    
            except Stock.DoesNotExist:
                # FIXED: Books without stock records are high priority
                stock_status = 'no_stock_record'
                current_stock = 0
                reorder_level = 10
                priority_level = 'high'
                priority_text = 'No Stock Record - High Priority'
            
            # Check existing vendor offers
            existing_offers = StockOffer.objects.filter(
                vendor=vendor_profile,
                book=book,
                status__in=['pending', 'approved']
            ).aggregate(
                total_pending=Sum('quantity', filter=Q(status='pending')),
                total_approved=Sum('quantity', filter=Q(status='approved'))
            )
            
            # Calculate suggested quantity based on stock status
            if stock_status in ['out_of_stock', 'no_stock_record']:
                suggested_qty = max(20, reorder_level + 10)  # Higher for out of stock
            elif stock_status == 'low_stock':
                suggested_qty = reorder_level - current_stock + 5
            else:
                suggested_qty = 5
            
            book_list.append({
                'id': book.id,
                'title': book.title,
                'authors': authors,
                'isbn': book.isbn,
                'category': book.category.name,
                'stock_status': stock_status,
                'current_stock': current_stock,
                'priority_level': priority_level,
                'priority_text': priority_text,
                'existing_pending': existing_offers['total_pending'] or 0,
                'existing_approved': existing_offers['total_approved'] or 0,
                'reorder_level': reorder_level,
                'suggested_quantity': suggested_qty,
                'book_status': book.status,  # Add book status for debugging
            })
        
        # Sort by priority (high priority first)
        priority_order = {'high': 0, 'medium': 1, 'normal': 2}
        book_list.sort(key=lambda x: priority_order.get(x['priority_level'], 3))
        
        return JsonResponse({'books': book_list})
        
    except Exception as e:
        return JsonResponse({'error': f'Search error: {str(e)}'}, status=500)

@login_required
def category_books_api(request):
    """FIXED: API that properly includes out-of-stock books in categories"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'error': 'Category ID is required'}, status=400)
    
    try:
        category = Category.objects.get(id=category_id)
        vendor_profile = get_object_or_404(VendorProfile, user=request.user)
        
        # FIXED: Include both available AND out_of_stock books
        books = Book.objects.filter(
            category=category,
            status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock
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
                
                # FIXED: Proper priority calculation
                if current_stock == 0:
                    stock_status = 'out_of_stock'
                    priority = 'high'
                    priority_text = 'OUT OF STOCK'
                elif current_stock <= reorder_level:
                    stock_status = 'low_stock'
                    priority = 'medium'
                    priority_text = 'LOW STOCK'
                else:
                    stock_status = 'in_stock'
                    priority = 'normal'
                    priority_text = 'IN STOCK'
                    
            except Stock.DoesNotExist:
                # FIXED: No stock record = high priority
                stock_status = 'no_stock_record'
                current_stock = 0
                reserved_stock = 0
                reorder_level = 10
                priority = 'high'
                priority_text = 'NO STOCK RECORD'
            
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
            
            # Calculate suggested quantity based on stock status
            if stock_status in ['out_of_stock', 'no_stock_record']:
                suggested_qty = max(25, reorder_level + 15)  # Higher for critical items
            elif stock_status == 'low_stock':
                suggested_qty = reorder_level - current_stock + 10
            else:
                suggested_qty = 5
            
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
                'priority_text': priority_text,
                'suggested_quantity': suggested_qty,
                'existing_pending': existing_offers['pending_quantity'] or 0,
                'existing_approved': existing_offers['approved_quantity'] or 0,
                'has_existing_offers': existing_offers['total_offers'] > 0,
                'last_offer_date': existing_offers['latest_offer_date'].isoformat() if existing_offers['latest_offer_date'] else None,
                'book_status': book.status,  # Add for debugging
            })
        
        # Sort by priority (high need first, then by title)
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
    """FIXED: Categories API that properly counts out-of-stock books"""
    try:
        # FIXED: Get categories with proper book filtering
        categories = Category.objects.filter(
            is_active=True,
            books__status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock
        ).distinct().annotate(
            total_books=Count('books', filter=Q(books__status__in=['available', 'out_of_stock']))
        ).filter(total_books__gt=0)
        
        category_list = []
        for category in categories:
            # FIXED: Get stock statistics for ALL books in category (including out_of_stock)
            category_books = Book.objects.filter(
                category=category, 
                status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock
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
            
            # Calculate priority based on critical needs
            needs_attention = out_of_stock + low_stock + no_stock_record
            if out_of_stock > 5 or needs_attention > 10:
                priority = 'high'
            elif out_of_stock > 2 or needs_attention > 5:
                priority = 'medium'
            else:
                priority = 'normal'
            
            # Calculate opportunity score
            opportunity_score = int((needs_attention / category.total_books) * 100) if category.total_books > 0 else 0
            
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
                'opportunity_score': opportunity_score,
                'urgency_message': f"{out_of_stock} books out of stock" if out_of_stock > 0 else f"{low_stock} books low stock" if low_stock > 0 else "Stock levels normal"
            })
        
        # Sort by priority and urgent needs
        category_list.sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1 if x['priority'] == 'medium' else 2,
            -x['out_of_stock_books'],  # Out of stock first
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
    """FIXED: Category bulk offer that properly includes out-of-stock books"""
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
            
            # FIXED: Get books that need restocking including out_of_stock status
            books_needing_stock = Book.objects.filter(
                category=category,
                status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock
            ).annotate(
                needs_restock=Case(
                    When(stock__isnull=True, then=1),  # No stock record
                    When(stock__available_quantity=0, then=1),   # Out of stock
                    When(stock__available_quantity__lte=F('stock__reorder_level'), then=1),  # Low stock
                    default=0,
                    output_field=IntegerField()
                )
            ).filter(needs_restock=1).exclude(
                # Don't include books with recent pending/approved offers
                stockoffer__vendor=vendor_profile,
                stockoffer__status__in=['pending', 'approved'],
                stockoffer__created_at__gte=timezone.now() - timezone.timedelta(days=7)
            )
            
            if not books_needing_stock.exists():
                messages.warning(
                    request,
                    f'No books in "{category.name}" currently need restocking, or you have recent pending offers for all books needing stock.'
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
    
    # Get priority categories with proper counting
    priority_categories = get_priority_categories_for_vendor(vendor_profile)
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
        'priority_categories': priority_categories,
    }
    
    return render(request, 'vendors/submit_category_bulk_offer.html', context)


# Helper Functions
def calculate_suggested_quantity(book):
    """FIXED: Calculate smart suggested quantity with better logic for out-of-stock"""
    try:
        stock = Stock.objects.get(book=book)
        reorder_level = stock.reorder_level
        current_stock = stock.available_quantity
        
        if current_stock == 0:
            # Out of stock - suggest higher quantity
            return max(25, reorder_level + 15)
        elif current_stock <= reorder_level:
            # Low stock - suggest to reach comfortable level
            return max(reorder_level - current_stock + 10, 10)
        else:
            # In stock - minimal quantity
            return 5
            
    except Stock.DoesNotExist:
        # No stock record - suggest substantial quantity
        return 20

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
    """FIXED: Get categories prioritized for vendor including out-of-stock books"""
    return Category.objects.filter(
        is_active=True,
        books__status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock
    ).annotate(
        # FIXED: Count books that need restocking
        needs_restock=Count('books', filter=Q(
            Q(books__stock__available_quantity__lte=F('books__stock__reorder_level')) |
            Q(books__stock__isnull=True),
            books__status__in=['available', 'out_of_stock']
        )),
        total_books=Count('books', filter=Q(books__status__in=['available', 'out_of_stock'])),
        out_of_stock_count=Count('books', filter=Q(
            books__stock__available_quantity=0,
            books__status__in=['available', 'out_of_stock']
        )),
        no_stock_count=Count('books', filter=Q(
            books__stock__isnull=True,
            books__status__in=['available', 'out_of_stock']
        )),
        vendor_recent_offers=Count('books__stockoffer', filter=Q(
            books__stockoffer__vendor=vendor_profile,
            books__stockoffer__created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ))
    ).filter(
        needs_restock__gt=0
    ).order_by('-out_of_stock_count', '-needs_restock', 'name')



def get_vendor_opportunities(vendor_profile):
    """FIXED: Get warehouse opportunities for vendor dashboard"""
    try:
        # FIXED: Count books that really need attention
        out_of_stock_books = Stock.objects.filter(
            available_quantity=0,
            book__status__in=['available', 'out_of_stock']  # FIXED: Include out_of_stock status
        ).count()
        
        low_stock_books = Stock.objects.filter(
            available_quantity__lte=F('reorder_level'),
            available_quantity__gt=0,
            book__status__in=['available', 'out_of_stock']
        ).count()
        
        # Books without stock records (also high priority)
        books_without_stock = Book.objects.filter(
            status__in=['available', 'out_of_stock'],
            stock__isnull=True
        ).count()
        
        # Categories needing attention
        categories_needing_attention = Category.objects.filter(
            is_active=True,
            books__status__in=['available', 'out_of_stock']
        ).annotate(
            out_of_stock_count=Count('books', filter=Q(
                books__stock__available_quantity=0
            )),
            no_stock_count=Count('books', filter=Q(
                books__stock__isnull=True,
                books__status__in=['available', 'out_of_stock']
            ))
        ).filter(
            Q(out_of_stock_count__gt=0) | Q(no_stock_count__gt=0)
        ).count()
        
        # Recent offers from this vendor to avoid double-offering
        recent_vendor_offers = StockOffer.objects.filter(
            vendor=vendor_profile,
            created_at__gte=timezone.now() - timezone.timedelta(days=7),
            status__in=['pending', 'approved']
        ).values_list('book_id', flat=True)
        
        # High priority books this vendor hasn't offered yet
        high_priority_opportunities = Stock.objects.filter(
            Q(available_quantity=0) | Q(book__stock__isnull=True),
            book__status__in=['available', 'out_of_stock']
        ).exclude(
            book_id__in=recent_vendor_offers
        ).count()
        
        return {
            'out_of_stock_books': out_of_stock_books,
            'low_stock_books': low_stock_books,
            'books_without_stock': books_without_stock,
            'total_opportunities': out_of_stock_books + low_stock_books + books_without_stock,
            'categories_needing_attention': categories_needing_attention,
            'high_priority_opportunities': high_priority_opportunities,
            'show_alerts': out_of_stock_books > 0 or books_without_stock > 0,
        }
        
    except Exception as e:
        print(f"Error calculating vendor opportunities: {e}")
        return {
            'out_of_stock_books': 0,
            'low_stock_books': 0,
            'books_without_stock': 0,
            'total_opportunities': 0,
            'categories_needing_attention': 0,
            'high_priority_opportunities': 0,
            'show_alerts': False,
        }




