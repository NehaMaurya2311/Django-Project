from django.core.management.base import BaseCommand
from books.models import Book
from warehouse.models import Stock

class Command(BaseCommand):
    help = 'Create Stock records for existing books that don\'t have them'
    
    def handle(self, *args, **options):
        books_without_stock = Book.objects.filter(stock__isnull=True)
        created_count = 0
        
        for book in books_without_stock:
            stock, created = Stock.objects.get_or_create(
                book=book,
                defaults={
                    'quantity': 0,
                    'reorder_level': 5,
                    'max_stock_level': 100,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created stock record for: {book.title}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} stock records')
        )
