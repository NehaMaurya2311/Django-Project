# delivery/urls.py
from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    # Customer tracking
    path('track/<str:order_id>/', views.track_delivery, name='track_delivery'),
    path('rate/<int:delivery_id>/', views.rate_delivery, name='rate_delivery'),
    
    # Staff/Admin dashboard and management
    path('dashboard/', views.delivery_dashboard, name='dashboard'),
    path('list/', views.delivery_list, name='delivery_list'),
    path('create/', views.create_delivery, name='create_delivery'),
    
    # Status and partner management
    path('update-status/<int:delivery_id>/', views.update_delivery_status, name='update_status'),
    path('assign-partner/<int:delivery_id>/', views.assign_partner, name='assign_partner'),
    path('bulk-assign/', views.bulk_assign_partners, name='bulk_assign_partners'),
    
    # Partner management
    path('partners/', views.partner_list, name='partner_list'),
    path('partners/create/', views.create_partner, name='create_partner'),
    path('partners/<int:partner_id>/edit/', views.edit_partner, name='edit_partner'),
    
    # API endpoints
    path('api/status/<str:tracking_id>/', views.delivery_status_api, name='delivery_status_api'),
]