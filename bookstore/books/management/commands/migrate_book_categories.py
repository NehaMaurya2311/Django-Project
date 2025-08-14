from django.core.management.base import BaseCommand
from books.models import Book, Category, SubCategory
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Migrates books to the new category and subcategory structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the changes that would be made without actually making them',
        )

    def split_category_string(self, category_string):
        """Split a category string into main category and subcategory"""
        if ' / ' in category_string:
            main_category, subcategory = category_string.split(' / ', 1)
            return main_category.strip(), subcategory.strip()
        return category_string.strip(), None

    def normalize_category_name(self, name):
        """Normalize category names for better matching"""
        # Remove extra whitespace and convert to title case
        name = ' '.join(name.split()).title()
        
        # Handle common variations
        replacements = {
            # Main categories
            'Juvenile Fiction': 'Young Adult Fiction',
            'Young Adult Literature': 'Young Adult Fiction',
            'Biographies & Autobiographies': 'Biography',
            'Autobiography': 'Biography',
            'Autobiographies': 'Biography',
            'Biographical': 'Biography',
            
            # Fiction genres
            'Romance Fiction': 'Romance',
            'Fantasy Fiction': 'Fantasy',
            'Science Fiction & Fantasy': 'Science Fiction',
            'Sci-Fi': 'Science Fiction',
            'Mystery Fiction': 'Mystery',
            'Horror Fiction': 'Horror',
            'Thriller Fiction': 'Thriller',
            'Adventure Fiction': 'Adventure',
            'Historical Fiction': 'Historical Fiction',
            
            # Young Adult variations
            'Juvenile Fiction': 'Young Adult Fiction',
            'Young Adult Literature': 'Young Adult Fiction',
            'Ya Fiction': 'Young Adult Fiction',
            'Teen Fiction': 'Young Adult Fiction',
            'Teenage Fiction': 'Young Adult Fiction',
            
            # Children's books variations
            'Children\'S Books': 'Children\'s Books',
            'Children\'S Fiction': 'Children\'s Books',
            'Children\'S Literature': 'Children\'s Books',
            'Children\'S Poetry': 'Children\'s Poetry',
            'Childrens Books': 'Children\'s Books',
            'Childrens Fiction': 'Children\'s Books',
            'Childrens Poetry': 'Children\'s Poetry',
            'Kids Books': 'Children\'s Books',
            
            # Non-fiction variations
            'History & Geography': 'History',
            'Health & Fitness': 'Health & Fitness',
            'Self Help': 'Self-Help',
            'Self-Help & Relationships': 'Self-Help',
            'Business & Economics': 'Business',
            'Computers & Technology': 'Technology',
            'Religion & Spirituality': 'Religion',
            'Philosophy & Religion': 'Philosophy',
            
            # Education
            'Education & Teaching': 'Education',
            'Study Aids': 'Education',
            'Reference': 'Reference',
            
            # Arts
            'Art & Design': 'Art & Design',
            'Music & Arts': 'Arts',
            'Photography': 'Photography',
            
            # Other common variations
            'True Crime': 'Crime',
            'Political Science': 'Politics',
            'Psychology & Counseling': 'Psychology',
            'Travel & Tourism': 'Travel',
            'Cooking & Food': 'Cooking',
            'Sports & Recreation': 'Sports',
        }
        
        return replacements.get(name, name)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write('Starting category migration...')
        
        # Get all books
        books = Book.objects.all()
        changes_made = 0
        errors = 0
        
        for book in books:
            try:
                # Get Google Books categories or use existing category
                if book.google_books_id:
                    # You would implement Google Books API call here to get categories
                    # For now, we'll use existing category if available
                    category_name = book.category.name if book.category else "General"
                else:
                    category_name = book.category.name if book.category else "General"
                
                # Split and normalize category names
                main_category_name, subcategory_name = self.split_category_string(category_name)
                normalized_category_name = self.normalize_category_name(main_category_name)
                
                if not dry_run:
                    # Get or create the main category
                    category, cat_created = Category.objects.get_or_create(
                        name=normalized_category_name,
                        defaults={
                            'slug': slugify(normalized_category_name),
                            'is_active': True
                        }
                    )
                    
                    # Handle subcategory if it exists
                    subcategory = None
                    if subcategory_name:
                        subcategory, subcat_created = SubCategory.objects.get_or_create(
                            category=category,
                            name=subcategory_name,
                            defaults={
                                'slug': slugify(subcategory_name),
                                'is_active': True
                            }
                        )
                    
                    # Check if changes are needed
                    needs_update = (
                        book.category != category or 
                        (subcategory and book.subcategory != subcategory) or
                        (not subcategory and book.subcategory is not None)
                    )
                    
                    if needs_update:
                        # Set the category and subcategory for the book
                        book.category = category
                        book.subcategory = subcategory
                        book.save()
                        changes_made += 1
                
                # Prepare status message
                status_msg = (
                    f'{"Would migrate" if dry_run else "Migrated"} book "{book.title}" to '
                    f'category "{normalized_category_name}"'
                )
                if subcategory_name:
                    status_msg += f' and subcategory "{subcategory_name}"'
                
                self.stdout.write(self.style.SUCCESS(status_msg))
            
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing book "{book.title}": {str(e)}'
                    )
                )
        
        summary = (
            f'\nMigration complete!\n'
            f'{"Would make" if dry_run else "Made"} {changes_made} changes\n'
            f'Encountered {errors} errors'
        )
        
        self.stdout.write(self.style.SUCCESS(summary))
