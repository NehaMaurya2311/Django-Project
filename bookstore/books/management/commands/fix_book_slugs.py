# Create this file: books/management/commands/fix_book_slugs.py

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from books.models import Book
import uuid

class Command(BaseCommand):
    help = 'Fix books with empty or invalid slugs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything',
        )

    def handle(self, *args, **options):
        # Find books with empty or null slugs
        books_without_slugs = Book.objects.filter(slug__isnull=True) | Book.objects.filter(slug='')
        
        if not books_without_slugs.exists():
            self.stdout.write(
                self.style.SUCCESS('No books found with missing slugs!')
            )
            return

        self.stdout.write(f'Found {books_without_slugs.count()} books with missing slugs')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        fixed_count = 0
        for book in books_without_slugs:
            base_slug = slugify(book.title)
            if not base_slug:
                base_slug = f"book-{uuid.uuid4().hex[:8]}"
            
            # Ensure slug is unique
            slug = base_slug
            counter = 1
            while Book.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            if options['dry_run']:
                self.stdout.write(f'Would fix: "{book.title}" -> "{slug}"')
            else:
                book.slug = slug
                book.save(update_fields=['slug'])
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed slug for book: "{book.title}" -> "{slug}"')
                )
        
        if not options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} books with missing slugs')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Would fix {books_without_slugs.count()} books. Run without --dry-run to apply changes.')
            )