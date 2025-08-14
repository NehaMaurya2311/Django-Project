# books/management/commands/fix_category_hierarchy.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db import transaction
from books.models import Category, SubCategory, SubSubCategory, Book

class Command(BaseCommand):
    help = 'Fix the category hierarchy by moving misplaced categories to proper structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Define the correct hierarchy structure
        correct_hierarchy = {
            'Fiction': {
                'General Fiction': ['Contemporary Fiction', 'Literary Fiction'],
                'Young Adult Fiction': ['YA Contemporary', 'YA Fantasy', 'YA Romance', 'YA Mystery'],
                'Romance': ['Contemporary Romance', 'Historical Romance', 'Paranormal Romance'],
                'Mystery & Thriller': ['Crime Fiction', 'Detective Stories', 'Psychological Thriller'],
                'Fantasy': ['Epic Fantasy', 'Urban Fantasy', 'Paranormal Fantasy'],
                'Science Fiction': ['Space Opera', 'Dystopian', 'Hard Science Fiction'],
                'Horror': ['Psychological Horror', 'Supernatural Horror', 'Gothic Horror'],
                'Historical Fiction': ['Historical Drama', 'War Fiction', 'Period Romance'],
                'Adventure': ['Action & Adventure', 'Military Fiction', 'Survival Stories'],
                'Classics': ['Literary Classics', 'Modern Classics', 'World Literature'],
                'Women\'s Fiction': ['Contemporary Women\'s Fiction', 'Family Saga', 'Book Club Fiction'],
            },
            'Non Fiction': {
                'Biography & Memoir': ['Celebrity Biographies', 'Political Memoirs', 'Sports Biographies'],
                'Business & Economics': ['Management & Leadership', 'Entrepreneurship', 'Finance & Investing'],
                'Health & Wellness': ['Diet & Nutrition', 'Mental Health', 'Fitness & Exercise'],
                'Self-Help & Personal Development': ['Motivational', 'Psychology', 'Productivity'],
                'History': ['World History', 'Indian History', 'Military History'],
                'Travel': ['Travel Guides', 'Travel Memoirs', 'Cultural Studies'],
                'Science & Nature': ['Popular Science', 'Environment', 'Technology'],
                'Philosophy': ['Western Philosophy', 'Eastern Philosophy', 'Ethics'],
                'Religion & Spirituality': ['Spiritual Growth', 'Religious Studies', 'Meditation'],
                'Reference': ['Dictionaries', 'Encyclopedias', 'Study Guides'],
                'Sports & Recreation': ['General Sports', 'Outdoor Activities', 'Games & Hobbies'],
            },
            'Children Books': {
                'Early Childhood (0-5)': ['Picture Books', 'Board Books', 'Nursery Rhymes'],
                'Elementary (5-8)': ['Beginning Readers', 'Early Chapter Books', 'Educational'],
                'Middle Grade (8-13)': ['Chapter Books', 'Adventure Stories', 'Mystery & Detective'],
            },
            'Comics & Manga': {
                'Comics': ['Superhero Comics', 'Independent Comics', 'Indian Comics'],
                'Manga': ['Shonen Manga', 'Shoujo Manga', 'Seinen Manga'],
                'Graphic Novels': ['Contemporary Graphic Novels', 'Historical Graphic Novels', 'Memoir Comics'],
            },
            'Coffee Table': {
                'Art & Photography': ['Fine Art', 'Photography', 'Design'],
                'Food & Cooking': ['International Cuisine', 'Baking & Desserts', 'Healthy Cooking'],
                'Design & Architecture': ['Interior Design', 'Architecture', 'Landscape Design'],
                'Transportation': ['Classic Cars', 'Aviation', 'Maritime'],
                'Nature & Wildlife': ['Wildlife Photography', 'Natural History', 'Conservation'],
                'Gardening & Landscaping': ['Garden Design', 'Plant Care', 'Organic Gardening'],
                'Entertainment': ['Cinema & Film', 'Music', 'Television'],
                'Lifestyle & Fashion': ['Fashion Photography', 'Style Guides', 'Cultural Trends'],
            },
            'Hindi Novels': {
                'Contemporary Hindi Literature': ['Modern Hindi Fiction', 'Hindi Poetry', 'Hindi Drama'],
                'Classic Hindi Literature': ['Traditional Hindi Literature', 'Sanskrit Literature'],
                'Dictionary & Language Studies': ['Hindi Grammar', 'Translation Studies', 'Language Learning'],
            }
        }

        # Step 1: Create proper hierarchy
        self.stdout.write('Creating proper category hierarchy...')
        
        with transaction.atomic():
            for main_cat_name, subcats in correct_hierarchy.items():
                # Get or create main category
                main_category, created = Category.objects.get_or_create(
                    name=main_cat_name,
                    defaults={
                        'slug': slugify(main_cat_name),
                        'description': f'{main_cat_name} books collection',
                        'is_active': True
                    }
                )
                
                if created and not dry_run:
                    self.stdout.write(f'  Created main category: {main_cat_name}')
                
                for subcat_name, subsubcats in subcats.items():
                    # Get or create subcategory
                    subcategory, sub_created = SubCategory.objects.get_or_create(
                        category=main_category,
                        name=subcat_name,
                        defaults={
                            'slug': slugify(subcat_name),
                            'description': f'{subcat_name} in {main_cat_name}',
                            'is_active': True
                        }
                    )
                    
                    if sub_created and not dry_run:
                        self.stdout.write(f'    Created subcategory: {subcat_name}')
                    
                    for subsubcat_name in subsubcats:
                        # Get or create sub-subcategory
                        subsubcategory, subsub_created = SubSubCategory.objects.get_or_create(
                            subcategory=subcategory,
                            name=subsubcat_name,
                            defaults={
                                'slug': slugify(subsubcat_name),
                                'description': f'{subsubcat_name} in {subcat_name}',
                                'is_active': True
                            }
                        )
                        
                        if subsub_created and not dry_run:
                            self.stdout.write(f'      Created sub-subcategory: {subsubcat_name}')

        # Step 2: Fix misplaced books
        self.stdout.write('\nFixing misplaced books...')
        
        # Handle specific cases like "Young Adult Fiction" being a main category
        wrong_categories = {
            'Young Adult Fiction': ('Fiction', 'Young Adult Fiction', 'YA Contemporary'),
            'General': ('Fiction', 'General Fiction', 'Contemporary Fiction'),
        }
        
        books_moved = 0
        
        with transaction.atomic():
            for wrong_cat_name, (correct_main, correct_sub, correct_subsub) in wrong_categories.items():
                try:
                    wrong_category = Category.objects.get(name=wrong_cat_name)
                    correct_category = Category.objects.get(name=correct_main)
                    correct_subcategory = SubCategory.objects.get(
                        category=correct_category, 
                        name=correct_sub
                    )
                    correct_subsubcategory = SubSubCategory.objects.get(
                        subcategory=correct_subcategory,
                        name=correct_subsub
                    )
                    
                    # Move all books from wrong category to correct hierarchy
                    books_to_move = Book.objects.filter(category=wrong_category)
                    count = books_to_move.count()
                    
                    if count > 0:
                        self.stdout.write(f'  Moving {count} books from "{wrong_cat_name}" to "{correct_main} > {correct_sub} > {correct_subsub}"')
                        
                        if not dry_run:
                            books_to_move.update(
                                category=correct_category,
                                subcategory=correct_subcategory,
                                subsubcategory=correct_subsubcategory
                            )
                            books_moved += count
                        
                        # Deactivate the wrong category if it's now empty
                        if not dry_run and wrong_category.books.count() == 0:
                            wrong_category.is_active = False
                            wrong_category.save()
                            self.stdout.write(f'    Deactivated empty category: {wrong_cat_name}')
                            
                except (Category.DoesNotExist, SubCategory.DoesNotExist, SubSubCategory.DoesNotExist):
                    self.stdout.write(f'  Skipping {wrong_cat_name} - target hierarchy not found')

        # Step 3: Assign books without subcategory/subsubcategory to default ones
        self.stdout.write('\nAssigning default subcategories and sub-subcategories...')
        
        default_assignments = {
            'Fiction': ('General Fiction', 'Contemporary Fiction'),
            'Non Fiction': ('Biography & Memoir', 'Celebrity Biographies'),
            'Children Books': ('Elementary (5-8)', 'Chapter Books'),
            'Comics & Manga': ('Comics', 'Superhero Comics'),
            'Coffee Table': ('Art & Photography', 'Fine Art'),
            'Hindi Novels': ('Contemporary Hindi Literature', 'Modern Hindi Fiction'),
        }
        
        books_updated = 0
        
        with transaction.atomic():
            for category in Category.objects.filter(is_active=True):
                if category.name in default_assignments:
                    default_sub_name, default_subsub_name = default_assignments[category.name]
                    
                    try:
                        default_subcategory = SubCategory.objects.get(
                            category=category,
                            name=default_sub_name
                        )
                        default_subsubcategory = SubSubCategory.objects.get(
                            subcategory=default_subcategory,
                            name=default_subsub_name
                        )
                        
                        # Books without subcategory
                        books_without_subcat = Book.objects.filter(
                            category=category,
                            subcategory__isnull=True
                        )
                        count_subcat = books_without_subcat.count()
                        
                        if count_subcat > 0:
                            self.stdout.write(f'  Assigning {count_subcat} books in "{category.name}" to default subcategory "{default_sub_name}"')
                            if not dry_run:
                                books_without_subcat.update(subcategory=default_subcategory)
                                books_updated += count_subcat
                        
                        # Books without sub-subcategory
                        books_without_subsubcat = Book.objects.filter(
                            category=category,
                            subcategory=default_subcategory,
                            subsubcategory__isnull=True
                        )
                        count_subsubcat = books_without_subsubcat.count()
                        
                        if count_subsubcat > 0:
                            self.stdout.write(f'  Assigning {count_subsubcat} books in "{category.name} > {default_sub_name}" to default sub-subcategory "{default_subsub_name}"')
                            if not dry_run:
                                books_without_subsubcat.update(subsubcategory=default_subsubcategory)
                                books_updated += count_subsubcat
                                
                    except (SubCategory.DoesNotExist, SubSubCategory.DoesNotExist):
                        self.stdout.write(f'  Warning: Default hierarchy not found for {category.name}')

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nDRY RUN COMPLETED. Would have moved {books_moved} books and updated {books_updated} book assignments.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nHIERARCHY FIX COMPLETED! Moved {books_moved} books and updated {books_updated} book assignments.')
            )
            self.stdout.write('Please run "python manage.py collectstatic" if you have static files that need updating.')
        
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Run migrations: python manage.py migrate')
        self.stdout.write('2. Test the admin interface')
        self.stdout.write('3. Update your navigation templates to show the new hierarchy')
        self.stdout.write('4. Test book addition from Google Books API with new category mapping')