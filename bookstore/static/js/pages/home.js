
document.addEventListener('DOMContentLoaded', () => {
    // Initialize all event handlers
    initializeTabSwitching();
    initializeBookCards();
    initializeCategoryCards();
    initializeSmoothScrolling();
    initializeScrollAnimation();
});

// Tab switching functionality
function initializeTabSwitching() {
    const tabContainer = document.querySelector('.book-section-nav');
    if (!tabContainer) return;

    tabContainer.addEventListener('click', (event) => {
        const tab = event.target.closest('.book-section-tab');
        if (!tab) return;

        const sectionType = tab.dataset.section;
        if (!sectionType) return;

        // Hide all sections
        document.querySelectorAll('.section-books').forEach(section => {
            section.classList.remove('active');
        });
        
        // Remove active class from all tabs
        document.querySelectorAll('.book-section-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show selected section and activate tab
        document.getElementById(`${sectionType}-books`).classList.add('active');
        tab.classList.add('active');
    });
}

// Book cards functionality
function initializeBookCards() {
    document.querySelectorAll('.book-card').forEach(card => {
        // Book detail click
        card.addEventListener('click', (event) => {
            if (!event.target.closest('.book-actions')) {
                const bookId = card.dataset.bookId;
                const bookUrl = `${window.bookstore.urls.bookDetail.replace('SLUG', bookId)}`;
                window.location.href = bookUrl;
            }
        });

        // Quick view button
        const quickViewBtn = card.querySelector('.quick-view-btn');
        if (quickViewBtn) {
            quickViewBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                const bookId = card.dataset.bookId;
                quickView(bookId);
            });
        }

        // Wishlist button
        const wishlistBtn = card.querySelector('.wishlist-btn');
        if (wishlistBtn) {
            wishlistBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                const bookId = card.dataset.bookId;
                toggleWishlist(bookId);
            });
        }

        // Share button
        const shareBtn = card.querySelector('.share-btn');
        if (shareBtn) {
            shareBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                const title = shareBtn.dataset.bookTitle;
                const url = shareBtn.dataset.bookUrl;
                shareBook(title, url);
            });
        }
    });
}

// Category cards functionality
function initializeCategoryCards() {
    document.querySelectorAll('.category-card').forEach(card => {
        card.addEventListener('click', () => {
            const slug = card.dataset.categorySlug;
            if (slug) {
                window.location.href = window.bookstore.urls.categoryBooks.replace('SLUG', slug);
            }
        });
    });
}

// Add to Cart Function
function addToCart(bookId) {
    if (!window.bookstore.isAuthenticated) {
        showNotification('Please login to add items to cart', 'warning');
        setTimeout(() => {
            window.location.href = window.bookstore.urls.login;
        }, 1500);
        return;
    }

    fetch(window.bookstore.urls.addToCart.replace('0', bookId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            updateCartCount(data.cart_total);
        }
    })
    .catch(error => {
        showNotification('Error adding to cart', 'error');
    });
}

// Quick View Function
function quickView(bookId) {
    // Implementation for quick view modal
    showNotification('Quick view feature coming soon!', 'info');
}

// Wishlist Toggle Function
function toggleWishlist(bookId) {
    if (!window.bookstore.isAuthenticated) {
        showNotification('Please login to add items to wishlist', 'warning');
        setTimeout(() => {
            window.location.href = window.bookstore.urls.login;
        }, 1500);
        return;
    }

    fetch(window.bookstore.urls.toggleWishlist.replace('0', bookId), {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const wishlistBtn = document.querySelector(`.book-card[data-book-id="${bookId}"] .wishlist-btn i`);
            if (wishlistBtn) {
                wishlistBtn.className = data.in_wishlist ? 'fas fa-heart' : 'far fa-heart';
            }
            showNotification(data.message, 'success');
        }
    })
    .catch(error => {
        showNotification('Error updating wishlist', 'error');
    });
}

// Share Book Function
function shareBook(title, url) {
    if (navigator.share) {
        navigator.share({
            title: title || 'Check out this book!',
            url: url || window.location.href
        }).catch(() => {
            copyToClipboard(url);
        });
    } else {
        copyToClipboard(url);
    }
}

// Copy to clipboard helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Link copied to clipboard!', 'success');
    }).catch(() => {
        showNotification('Failed to copy link', 'error');
    });
}

// Utility Functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : type === 'info' ? 'info-circle' : 'exclamation-triangle'}"></i>
        <span>${message}</span>
    `;
    
    // Add notification styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : type === 'info' ? '#17a2b8' : '#ffc107'};
        color: ${type === 'warning' ? '#333' : 'white'};
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 10px;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        max-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

function updateCartCount(count) {
    const cartCounter = document.querySelector('.cart-count');
    if (cartCounter) {
        cartCounter.textContent = count;
        cartCounter.style.animation = 'bounce 0.5s ease';
    }
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Add animation to book cards on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.6s ease-out';
        }
    });
}, observerOptions);

// Observe all book cards
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.book-card').forEach(card => {
        observer.observe(card);
    });
});
