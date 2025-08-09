from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 
                   'is_active', 'is_email_verified', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_email_verified', 'is_staff', 
                  'created_at', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone',
                                       'date_of_birth', 'profile_picture')}),
        (_('Address'), {'fields': ('address', 'city', 'state', 'pincode')}),
        (_('Account Type'), {'fields': ('user_type',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser',
                      'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Additional Info'), {'fields': ('preferences',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')
