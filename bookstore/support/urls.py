# support/urls.py
from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # FAQ and Help Center URLs
    path('faq/', views.faq, name='faq'),
    # Customer URLs
    path('', views.my_tickets, name='my_tickets'),
    path('create/', views.create_ticket, name='create_ticket'),
    path('ticket/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<str:ticket_id>/rate/', views.rate_ticket, name='rate_ticket'),
    
    # Live Chat URLs
    path('chat/start/', views.start_chat, name='start_chat'),
    path('chat/<str:session_id>/', views.chat_room, name='chat_room'),
    path('chat/<str:session_id>/send/', views.send_message, name='send_message'),
    path('chat/<str:session_id>/messages/', views.get_messages, name='get_messages'),
    path('chat/<str:session_id>/end/', views.end_chat, name='end_chat'),
    
    # Admin URLs
    path('admin/', views.admin_tickets, name='admin_tickets'),
    path('admin/ticket/<str:ticket_id>/', views.admin_ticket_detail, name='admin_ticket_detail'),
    path('admin/chats/', views.admin_live_chats, name='admin_live_chats'),
    path('admin/chat/<str:session_id>/', views.admin_join_chat, name='admin_join_chat'),
]