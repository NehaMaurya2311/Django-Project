# books/context_processors.py - Enhanced version
from django.db import connection
from django.core.cache import cache
from .models import Category, SubCategory, SubSubCategory, Cart

def cart_processor(request):
    """Context processor for cart information"""
    cart_total = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_total = cart.total_items
        except Cart.DoesNotExist:
            cart_total = 0
    
    return {'cart_total': cart_total}

def categories_processor(request):
    """Enhanced context processor for category hierarchy with caching"""
    
    # Use cache to avoid repeated database queries
    cache_key = 'navigation_categories_hierarchy'
    categories_data = cache.get(cache_key)
    
    if not categories_data:
        # Fetch categories with their subcategories and sub-subcategories
        categories = Category.objects.filter(is_active=True).prefetch_related(
            'subcategories__subsubcategories'
        ).order_by('name')
        
        # Build the hierarchy data structure
        categories_hierarchy = []
        
        for category in categories:
            category_data = {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'image': category.image,
                'subcategories': []
            }
            
            # Get active subcategories
            for subcategory in category.subcategories.filter(is_active=True).order_by('name'):
                subcategory_data = {
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'slug': subcategory.slug,
                    'description': subcategory.description,
                    'subsubcategories': []
                }
                
                # Get active sub-subcategories
                for subsubcategory in subcategory.subsubcategories.filter(is_active=True).order_by('name'):
                    subsubcategory_data = {
                        'id': subsubcategory.id,
                        'name': subsubcategory.name,
                        'slug': subsubcategory.slug,
                        'description': subsubcategory.description,
                    }
                    subcategory_data['subsubcategories'].append(subsubcategory_data)
                
                category_data['subcategories'].append(subcategory_data)
            
            categories_hierarchy.append(category_data)
        
        categories_data = {
            'categories': categories,  # Original QuerySet for backward compatibility
            'categories_hierarchy': categories_hierarchy,  # Structured hierarchy
        }
        
        # Cache for 30 minutes
        cache.set(cache_key, categories_data, 60 * 30)
    
    return categories_data

def breadcrumb_processor(request):
    """Context processor for generating breadcrumbs"""
    breadcrumbs = []
    
    # Add home breadcrumb
    breadcrumbs.append({
        'name': 'Home',
        'url': '/',
        'is_active': False
    })
    
    # Parse URL to determine current location
    path = request.path
    
    # Handle book detail pages
    if path.startswith('/book/'):
        breadcrumbs.append({
            'name': 'Books',
            'url': '/books/',
            'is_active': False
        })
        
        # If we can determine the current book, add category breadcrumbs
        if hasattr(request, 'resolver_match') and request.resolver_match:
            if 'slug' in request.resolver_match.kwargs:
                try:
                    from .models import Book
                    book = Book.objects.select_related(
                        'category', 'subcategory', 'subsubcategory'
                    ).get(slug=request.resolver_match.kwargs['slug'])
                    
                    # Add category breadcrumb
                    breadcrumbs.append({
                        'name': book.category.name,
                        'url': f'/category/{book.category.slug}/',
                        'is_active': False
                    })
                    
                    # Add subcategory breadcrumb if exists
                    if book.subcategory:
                        breadcrumbs.append({
                            'name': book.subcategory.name,
                            'url': f'/category/{book.category.slug}/{book.subcategory.slug}/',
                            'is_active': False
                        })
                        
                        # Add sub-subcategory breadcrumb if exists
                        if book.subsubcategory:
                            breadcrumbs.append({
                                'name': book.subsubcategory.name,
                                'url': f'/category/{book.category.slug}/{book.subcategory.slug}/{book.subsubcategory.slug}/',
                                'is_active': False
                            })
                    
                    # Add current book
                    breadcrumbs.append({
                        'name': book.title,
                        'url': path,
                        'is_active': True
                    })
                except:
                    pass
    
    # Handle category pages
    elif path.startswith('/category/'):
        breadcrumbs.append({
            'name': 'Books',
            'url': '/books/',
            'is_active': False
        })
        
        path_parts = path.strip('/').split('/')
        if len(path_parts) >= 2:  # category/slug/
            try:
                category = Category.objects.get(slug=path_parts[1])
                breadcrumbs.append({
                    'name': category.name,
                    'url': f'/category/{category.slug}/',
                    'is_active': len(path_parts) == 2
                })
                
                if len(path_parts) >= 3:  # category/slug/subcategory/
                    try:
                        subcategory = SubCategory.objects.get(slug=path_parts[2], category=category)
                        breadcrumbs.append({
                            'name': subcategory.name,
                            'url': f'/category/{category.slug}/{subcategory.slug}/',
                            'is_active': len(path_parts) == 3
                        })
                        
                        if len(path_parts) >= 4:  # category/slug/subcategory/subsubcategory/
                            try:
                                subsubcategory = SubSubCategory.objects.get(
                                    slug=path_parts[3], subcategory=subcategory
                                )
                                breadcrumbs.append({
                                    'name': subsubcategory.name,
                                    'url': f'/category/{category.slug}/{subcategory.slug}/{subsubcategory.slug}/',
                                    'is_active': True
                                })
                            except SubSubCategory.DoesNotExist:
                                pass
                    except SubCategory.DoesNotExist:
                        pass
            except Category.DoesNotExist:
                pass
    
    # Handle other pages
    elif path.startswith('/books/'):
        breadcrumbs.append({
            'name': 'All Books',
            'url': '/books/',
            'is_active': True
        })
    elif path.startswith('/search/'):
        breadcrumbs.append({
            'name': 'Search Results',
            'url': path,
            'is_active': True
        })
    
    return {'breadcrumbs': breadcrumbs}

def site_stats_processor(request):
    """Context processor for site statistics"""
    cache_key = 'site_stats'
    stats = cache.get(cache_key)
    
    if not stats:
        from .models import Book, Author, Publisher
        
        stats = {
            'total_books': Book.objects.filter(status='available').count(),
            'total_authors': Author.objects.count(),
            'total_publishers': Publisher.objects.count(),
            'total_categories': Category.objects.filter(is_active=True).count(),
        }
        
        # Cache for 1 hour
        cache.set(cache_key, stats, 60 * 60)
    
    return {'site_stats': stats}