
# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomUserRegistrationForm, ProfileUpdateForm
from .models import CustomUser

class SignUpView(CreateView):
    model = CustomUser
    form_class = CustomUserRegistrationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please log in.')
        return response

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    context = {
        'user': user,
    }
    
    if user.user_type == 'customer':
        from orders.models import Order
        from wishlist.models import WishlistItem
        
        recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
        wishlist_count = WishlistItem.objects.filter(user=user).count()
        
        context.update({
            'recent_orders': recent_orders,
            'wishlist_count': wishlist_count,
        })
        
    elif user.user_type == 'vendor':
        from vendors.models import VendorProfile, StockOffer
        
        vendor_profile = VendorProfile.objects.filter(user=user).first()
        recent_offers = StockOffer.objects.filter(vendor=vendor_profile).order_by('-created_at')[:5]
        
        context.update({
            'vendor_profile': vendor_profile,
            'recent_offers': recent_offers,
        })
    
    return render(request, 'accounts/dashboard.html', context)
