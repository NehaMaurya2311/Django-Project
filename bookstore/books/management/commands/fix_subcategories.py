# books/management/commands/fix_subcategories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from books.models import Category, SubCategory

class Command(BaseCommand):
    help = 'Fix subcategory slugs and ensure proper category structure'

    def handle(self, *args, **options):
        # Expected category structure with proper slugs
        expected_structure = {
            'Fiction': {
                'slug': 'fiction',
                'subcategories': {
                    'Fiction Reads': 'fiction-reads',
                    'Adventure': 'adventure', 
                    'Classic Novels': 'classic-novels',
                    'Mystery, Crime & Thriller': 'mystery-crime-thriller',
                    'Romance': 'romance',
                    'Young Adult Fiction': 'young-adult-fiction',  # This was the missing one
                    'Horror': 'horror',
                    'Fantasy': 'fantasy',
                    'Erotic Fiction': 'erotic-fiction',
                    "Women's Fiction": 'womens-fiction',
                    'Science Fiction': 'science-fiction',
                    'Historical Fiction': 'historical-fiction',
                }
            },
            'Non Fiction': {
                'slug': 'non-fiction',
                'subcategories': {
                    'Biography': 'biography',
                    'Self Help': 'self-help',
                    'Business & Management': 'business-management',
                    'Health & Fitness': 'health-fitness',
                    'Spirituality': 'spirituality',
                    'Philosophy': 'philosophy',
                    'History': 'history',
                    'Travel & Holiday': 'travel-holiday',
                    'Science & Nature': 'science-nature',
                    'Sports': 'sports',
                    'Dictionary & Reference': 'dictionary-reference',
                    'Stock Market Books': 'stock-market-books',
                }
            },
            'Coffee Table': {
                'slug': 'coffee-table',
                'subcategories': {
                    'History': 'history',
                    'Sports': 'sports',
                    'Food & Beverage': 'food-beverage',
                    'Interior Designing': 'interior-designing',
                    'Films & Animations': 'films-animations',
                    'Cars & Motorcycles': 'cars-motorcycles',
                    'Travel & Culture': 'travel-culture',
                    'Wildlife & Nature': 'wildlife-nature',
                    'Gardening': 'gardening',
                    'Science': 'science',
                    'Lifestyle & Fashion': 'lifestyle-fashion',
                    'Art, Painting & Music': 'art-painting-music',
                }
            },
            'Hindi Novels': {
                'slug': 'hindi-novels',
                'subcategories': {
                    'Dictionary & Language Studies': 'dictionary-language-studies',
                }
            },
            'Comics & Manga': {
                'slug': 'comics-manga',
                'subcategories': {
                    'Indian Comics': 'indian-comics',
                    'American Comics': 'american-comics', 
                    'Manga': 'manga',
                    'Graphic Novels': 'graphic-novels',
                }
            },
            'Children Books': {
                'slug': 'children-books',
                'subcategories': {
                    'Age 0 - 5 Years': 'age-0-5-years',
                    'Age 5 - 8 Years': 'age-5-8-years',
                    'Age 8 - 13 Years': 'age-8-13-years',
                }
            },
        }

        self.stdout.write(self.style.SUCCESS('Starting category and subcategory fix...'))
        
        for category_name, category_data in expected_structure.items():
            # Get or create category
            try:
                category = Category.objects.get(name=category_name)
                self.stdout.write(f'Found category: {category_name}')
                
                # Update slug if needed
                if category.slug != category_data['slug']:
                    old_slug = category.slug
                    category.slug = category_data['slug']
                    category.save()
                    self.stdout.write(
                        self.style.WARNING(f'Updated {category_name} slug from "{old_slug}" to "{category.slug}"')
                    )
                
            except Category.DoesNotExist:
                category = Category.objects.create(
                    name=category_name,
                    slug=category_data['slug'],
                    description=f'{category_name} books collection',
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created category: {category_name}'))

            # Process subcategories
            for subcat_name, expected_slug in category_data['subcategories'].items():
                try:
                    # Try to find existing subcategory by name
                    subcategory = SubCategory.objects.get(category=category, name=subcat_name)
                    
                    # Check if slug needs updating
                    if subcategory.slug != expected_slug:
                        old_slug = subcategory.slug
                        subcategory.slug = expected_slug
                        subcategory.save()
                        self.stdout.write(
                            self.style.WARNING(
                                f'Updated subcategory "{subcat_name}" slug from "{old_slug}" to "{expected_slug}"'
                            )
                        )
                    else:
                        self.stdout.write(f'  ✓ Subcategory "{subcat_name}" already has correct slug')
                        
                except SubCategory.DoesNotExist:
                    # Create missing subcategory
                    subcategory = SubCategory.objects.create(
                        category=category,
                        name=subcat_name,
                        slug=expected_slug,
                        description=f'{subcat_name} in {category_name}',
                        is_active=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'  + Created subcategory: {subcat_name} ({expected_slug})')
                    )

        # Check for any orphaned subcategories that don't match our structure
        self.stdout.write(self.style.SUCCESS('\nChecking for orphaned subcategories...'))
        
        all_expected_slugs = set()
        for category_data in expected_structure.values():
            all_expected_slugs.update(category_data['subcategories'].values())
        
        orphaned = SubCategory.objects.exclude(slug__in=all_expected_slugs)
        if orphaned.exists():
            self.stdout.write(self.style.WARNING('Found orphaned subcategories:'))
            for subcat in orphaned:
                self.stdout.write(f'  - {subcat.category.name} > {subcat.name} ({subcat.slug})')
                
                # Ask if user wants to keep or remove (for safety, just report)
                self.stdout.write(
                    self.style.WARNING(
                        f'    Note: This subcategory might need manual review. '
                        f'It has {subcat.books.count()} books assigned.'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('No orphaned subcategories found.'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== SUMMARY ==='))
        for category in Category.objects.all():
            subcat_count = category.subcategories.count()
            book_count = category.books.count() + sum(sc.books.count() for sc in category.subcategories.all())
            self.stdout.write(f'{category.name}: {subcat_count} subcategories, {book_count} books')
        
        self.stdout.write(self.style.SUCCESS('\nCategory structure fix completed successfully!'))
        self.stdout.write(self.style.SUCCESS('You can now navigate to subcategories from the navbar.'))