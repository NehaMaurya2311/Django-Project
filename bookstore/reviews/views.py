# reviews/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Avg
from books.models import Book
from orders.models import OrderItem
from .models import Review, ReviewHelpful
from .forms import ReviewForm

def book_reviews(request, slug):
    book = get_object_or_404(Book, slug=slug)
    
    reviews_list = Review.objects.filter(book=book, status='approved').select_related('user').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reviews_list, 5)
    page_number = request.GET.get('page')
    reviews = paginator.get_page(page_number)
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews_list.filter(rating=i).count()
    
    # Average rating
    avg_rating = reviews_list.aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'book': book,
        'reviews': reviews,
        'rating_distribution': rating_distribution,
        'avg_rating': round(avg_rating, 1),
        'total_reviews': reviews_list.count(),
    }
    
    return render(request, 'reviews/book_reviews.html', context)

@login_required
def write_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check if user has already reviewed this book
    existing_review = Review.objects.filter(book=book, user=request.user).first()
    if existing_review:
        messages.info(request, 'You have already reviewed this book. You can edit your existing review.')
        return redirect('reviews:edit_review', review_id=existing_review.id)
    
    # Check if user has purchased this book
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        book=book,
        order__status='delivered'
    ).exists()
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.user = request.user
            review.is_verified_purchase = has_purchased
            review.save()
            
            messages.success(request, 'Your review has been submitted and is pending approval.')
            return redirect('books:book_detail', slug=book.slug)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'book': book,
        'has_purchased': has_purchased,
    }
    
    return render(request, 'reviews/write_review.html', context)

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.status = 'pending'  # Reset to pending after edit
            review.save()
            
            messages.success(request, 'Your review has been updated and is pending approval.')
            return redirect('books:book_detail', slug=review.book.slug)
    else:
        form = ReviewForm(instance=review)
    
    context = {
        'form': form,
        'review': review,
    }
    
    return render(request, 'reviews/edit_review.html', context)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        book_slug = review.book.slug
        review.delete()
        messages.success(request, 'Your review has been deleted.')
        return redirect('books:book_detail', slug=book_slug)
    
    return render(request, 'reviews/delete_review.html', {'review': review})

@login_required
def mark_helpful(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        
        helpful_vote, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=request.user,
            defaults={'is_helpful': True}
        )
        
        if not created:
            # User already voted, toggle the vote
            helpful_vote.is_helpful = not helpful_vote.is_helpful
            helpful_vote.save()
        
        # Update helpful count
        helpful_count = ReviewHelpful.objects.filter(review=review, is_helpful=True).count()
        review.helpful_count = helpful_count
        review.save()
        
        return JsonResponse({
            'success': True,
            'helpful_count': helpful_count,
            'user_found_helpful': helpful_vote.is_helpful
        })
    
    return JsonResponse({'success': False})

@login_required
def my_reviews(request):
    reviews_list = Review.objects.filter(user=request.user).select_related('book').order_by('-created_at')
    
    paginator = Paginator(reviews_list, 10)
    page_number = request.GET.get('page')
    reviews = paginator.get_page(page_number)
    
    return render(request, 'reviews/my_reviews.html', {'reviews': reviews})
