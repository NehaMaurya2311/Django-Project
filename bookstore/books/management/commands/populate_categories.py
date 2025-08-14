# books/management/commands/populate_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from books.models import Category, SubCategory

class Command(BaseCommand):
    help = 'Populate categories and subcategories based on navbar structure'

    def handle(self, *args, **options):
        # Define the category structure from navbar.html
        categories_data = {
            'Fiction': {
                'description': 'Novels & Stories',
                'subcategories': [
                    'Fiction Reads',
                    'Adventure', 
                    'Classic Novels',
                    'Mystery, Crime & Thriller',
                    'Romance',
                    'Young Adult Fiction',
                    'Horror',
                    'Fantasy',
                    'Science Fiction',
                    'Historical Fiction',
                    'Women\'s Fiction'
                ]
            },
            'Non Fiction': {
                'description': 'Knowledge & Learning',
                'subcategories': [
                    'Biography',
                    'Self Help',
                    'Business & Management', 
                    'Health & Fitness',
                    'Spirituality',
                    'Philosophy',
                    'History',
                    'Travel & Holiday',
                    'Science & Nature',
                    'Sports',
                    'Dictionary & Reference',
                    'Stock Market Books'
                ]
            },
            'Coffee Table': {
                'description': 'Visual & Art Books',
                'subcategories': [
                    'Art, Painting & Music',
                    'Food & Beverage',
                    'Interior Designing',
                    'Films & Animations',
                    'Cars & Motorcycles',
                    'Travel & Culture',
                    'Wildlife & Nature',
                    'Gardening',
                    'Science',
                    'Lifestyle & Fashion',
                    'History',
                    'Sports'
                ]
            },
            'Hindi Novels': {
                'description': 'Indian Language Books',
                'subcategories': [
                    'Dictionary & Language Studies',
                    'Hindi Fiction',
                    'Hindi Poetry',
                    'Hindi Non-Fiction'
                ]
            },
            'Comics & Manga': {
                'description': 'Graphic Novels & Comics',
                'subcategories': [
                    'Indian Comics',
                    'American Comics',
                    'Manga',
                    'Graphic Novels'
                ]
            },
            'Children Books': {
                'description': 'Books for Young Readers',
                'subcategories': [
                    'Age 0 - 5 Years',
                    'Age 5 - 8 Years',
                    'Age 8 - 13 Years',
                    'Educational Books',
                    'Picture Books'
                ]
            }
        }

        created_categories = 0
        created_subcategories = 0

        # Create categories and subcategories
        for category_name, category_info in categories_data.items():
            # Create or get category
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={
                    'slug': slugify(category_name),
                    'description': category_info['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_categories += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category_name}')
                )
            
            # Create subcategories
            for subcategory_name in category_info['subcategories']:
                subcategory, created = SubCategory.objects.get_or_create(
                    category=category,
                    name=subcategory_name,
                    defaults={
                        'slug': slugify(subcategory_name),
                        'description': f'{subcategory_name} in {category_name}',
                        'is_active': True
                    }
                )
                
                if created:
                    created_subcategories += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created subcategory: {subcategory_name}')
                    )

        # Remove any juvenile/unwanted subcategories
        unwanted_subcategories = [
            'Juvenile Fiction',
            'Juvenile Nonfiction',
            'Young Adult',
            'Children\'s Books',
            'Kids Books'
        ]
        
        removed_count = 0
        for unwanted_name in unwanted_subcategories:
            deleted_count = SubCategory.objects.filter(name__icontains=unwanted_name).delete()[0]
            if deleted_count > 0:
                removed_count += deleted_count
                self.stdout.write(
                    self.style.WARNING(f'Removed unwanted subcategory: {unwanted_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:\n'
                f'Categories created: {created_categories}\n'
                f'Subcategories created: {created_subcategories}\n'
                f'Unwanted subcategories removed: {removed_count}\n'
                f'\nCategory structure updated successfully!'
            )
        )