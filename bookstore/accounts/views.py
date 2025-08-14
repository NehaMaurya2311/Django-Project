# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.forms import AuthenticationForm

# Import your actual forms
from .forms import CustomUserRegistrationForm, ProfileUpdateForm
from .models import CustomUser

class SignUpView(CreateView):
    model = CustomUser
    form_class = CustomUserRegistrationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            # Save the user
            user = form.save()
            
            # Automatically log the user in after successful signup
            login(self.request, user)
            
            # Add success message
            messages.success(self.request, 'Welcome to BookStore! Your account has been created successfully.')
            
            # Redirect to dashboard or home page (NOT login page)
            return redirect('accounts:dashboard')  # or 'books:home' if you have it
            
        except Exception as e:
            # If there's any error during user creation
            messages.error(self.request, f'Error creating account: {str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle form validation errors"""
        # Add error message
        messages.error(self.request, 'Please correct the errors below.')
        
        # Print errors to console for debugging
        print("Form validation errors:")
        for field, errors in form.errors.items():
            print(f"{field}: {errors}")
        
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context if needed"""
        context = super().get_context_data(**kwargs)
        # Add any additional context here
        return context


@login_required
def profile_view(request):
    return render(request, 'accounts/dashboard.html')

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
    context = {
        'user': request.user,
    }
    
    # Add customer-specific data
    if request.user.user_type == 'customer':
        # Add customer specific context
        context.update({
            'recent_orders': [],  # Add actual order queryset when Order model is available
            'wishlist_count': 0,  # Add actual wishlist count when Wishlist model is available
        })
    
    # Add vendor-specific data
    elif request.user.user_type == 'vendor':
        if hasattr(request.user, 'vendor_profile'):
            vendor_profile = request.user.vendor_profile
            
            # Calculate open tickets count
            open_tickets_count = vendor_profile.tickets.filter(
                status__in=['open', 'in_progress']
            ).count()
            
            context.update({
                'vendor_profile': vendor_profile,
                'open_tickets_count': open_tickets_count,
            })
    
    # Add admin/staff-specific data
    elif request.user.user_type in ['staff', 'admin'] or request.user.is_superuser:
        # Add admin specific context
        context.update({
            'total_users': CustomUser.objects.count(),
            'pending_vendors': 0,  # Add actual count when VendorProfile model is available
            'active_orders': 0,    # Add actual count when Order model is available
        })
    
    return render(request, 'accounts/dashboard.html', context)

def custom_logout_view(request):
    """Custom logout view that handles both GET and POST requests"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')