from django.shortcuts import render

# Create your views here.

# vendors/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from .models import VendorProfile, StockOffer, VendorTicket
from .forms import VendorRegistrationForm, StockOfferForm, VendorTicketForm

@login_required
def vendor_register(request):
    if hasattr(request.user, 'vendor_profile'):
        return redirect('vendors:dashboard')
    
    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            vendor_profile = form.save(commit=False)
            vendor_profile.user = request.user
            vendor_profile.save()
            
            # Update user type
            request.user.user_type = 'vendor'
            request.user.save()
            
            messages.success(request, 'Vendor registration submitted successfully! Please wait for approval.')
            return redirect('vendors:dashboard')
    else:
        form = VendorRegistrationForm()
    
    return render(request, 'vendors/register.html', {'form': form})

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
    
    # Recent offers
    recent_offers = StockOffer.objects.filter(vendor=vendor_profile).order_by('-created_at')[:5]
    
    # Open tickets
    open_tickets = VendorTicket.objects.filter(vendor=vendor_profile, status__in=['open', 'in_progress']).count()
    
    context = {
        'vendor_profile': vendor_profile,
        'total_offers': total_offers,
        'pending_offers': pending_offers,
        'approved_offers': approved_offers,
        'recent_offers': recent_offers,
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
