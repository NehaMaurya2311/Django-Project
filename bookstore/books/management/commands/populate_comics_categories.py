# books/management/commands/populate_comics_categories.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from books.models import Category, SubCategory, SubSubCategory


class Command(BaseCommand):
    help = 'Populate Comics & Manga category hierarchy'
    
    def handle(self, *args, **options):
        # Get or create Comics & Manga category
        comics_category, created = Category.objects.get_or_create(
            name='Comics & Manga',
            defaults={
                'slug': 'comics-manga',
                'description': 'Comics, Manga, and Graphic Novels collection',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created category: {comics_category.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Category already exists: {comics_category.name}')
            )
        
        # Define subcategories and their sub-subcategories
        categories_structure = {
            'Comics': {
                'description': 'Western style comics and graphic novels',
                'subsubcategories': [
                    'Superhero Comics',
                    'Independent Comics', 
                    'DC Comics',
                    'Marvel Comics',
                    'Dark Horse Comics',
                    'Image Comics',
                    'Vertigo Comics',
                    'Alternative Comics'
                ]
            },
            'Manga': {
                'description': 'Japanese style comics and graphic novels',
                'subsubcategories': [
                    'Shonen Manga',
                    'Shojo Manga', 
                    'Seinen Manga',
                    'Josei Manga',
                    'Kodomomuke Manga',
                    'Yaoi/BL Manga',
                    'Yuri/GL Manga',
                    'Doujinshi'
                ]
            },
            'Graphic Novels': {
                'description': 'Long-form graphic storytelling',
                'subsubcategories': [
                    'Contemporary Graphic Novels',
                    'Historical Graphic Novels',
                    'Biographical Graphic Novels',
                    'Science Fiction Graphic Novels',
                    'Fantasy Graphic Novels',
                    'Horror Graphic Novels',
                    'Romance Graphic Novels',
                    'Educational Graphic Novels'
                ]
            },
            'Webcomics': {
                'description': 'Comics originally published on the web',
                'subsubcategories': [
                    'Daily Strip Comics',
                    'Long-form Webcomics',
                    'Gag Comics',
                    'Story-driven Webcomics'
                ]
            },
            'Light Novels': {
                'description': 'Japanese young adult novels with illustrations',
                'subsubcategories': [
                    'Fantasy Light Novels',
                    'Romance Light Novels',
                    'Isekai Light Novels',
                    'Slice of Life Light Novels',
                    'Action Light Novels',
                    'Mystery Light Novels'
                ]
            },
            'Manhwa': {
                'description': 'Korean comics and graphic novels',
                'subsubcategories': [
                    'Romance Manhwa',
                    'Action Manhwa',
                    'Fantasy Manhwa',
                    'Historical Manhwa',
                    'Slice of Life Manhwa',
                    'Webtoons'
                ]
            }
        }
        
        # Create subcategories and sub-subcategories
        for subcategory_name, subcategory_data in categories_structure.items():
            # Create subcategory
            subcategory, sub_created = SubCategory.objects.get_or_create(
                category=comics_category,
                name=subcategory_name,
                defaults={
                    'slug': slugify(subcategory_name),
                    'description': subcategory_data['description'],
                    'is_active': True
                }
            )
            
            if sub_created:
                self.stdout.write(
                    self.style.SUCCESS(f'  Created subcategory: {subcategory.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  Subcategory already exists: {subcategory.name}')
                )
            
            # Create sub-subcategories
            for subsubcategory_name in subcategory_data['subsubcategories']:
                subsubcategory, subsub_created = SubSubCategory.objects.get_or_create(
                    subcategory=subcategory,
                    name=subsubcategory_name,
                    defaults={
                        'slug': slugify(subsubcategory_name),
                        'description': f'{subsubcategory_name} within {subcategory_name}',
                        'is_active': True
                    }
                )
                
                if subsub_created:
                    self.stdout.write(
                        self.style.SUCCESS(f'    Created sub-subcategory: {subsubcategory.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'    Sub-subcategory already exists: {subsubcategory.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS('\nSuccessfully populated Comics & Manga category hierarchy!')
        )
        
        # Show summary
        total_subcategories = SubCategory.objects.filter(category=comics_category).count()
        total_subsubcategories = SubSubCategory.objects.filter(
            subcategory__category=comics_category
        ).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:'
                f'\n- Category: {comics_category.name}'
                f'\n- Subcategories: {total_subcategories}'
                f'\n- Sub-subcategories: {total_subsubcategories}'
            )
        )