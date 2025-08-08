# reviews/urls.py
from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('book/<slug:slug>/', views.book_reviews, name='book_reviews'),
    path('write/<int:book_id>/', views.write_review, name='write_review'),
    path('edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('delete/<int:review_id>/', views.delete_review, name='delete_review'),
    path('helpful/<int:review_id>/', views.mark_helpful, name='mark_helpful'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
]
