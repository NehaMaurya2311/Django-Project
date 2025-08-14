# warehouse/management/commands/create_missing_stock_records.py

from django.core.management.base import BaseCommand
from books.models import Book
from warehouse.models import Stock

class Command(BaseCommand):
    help = 'Create stock records for books that don\'t have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-quantity',
            type=int,
            default=0,
            help='Default stock quantity for new records (default: 0)'
        )
        parser.add_argument(
            '--default-reorder-level',
            type=int,
            default=10,
            help='Default reorder level (default: 10)'
        )

    def handle(self, *args, **options):
        default_quantity = options['default_quantity']
        default_reorder_level = options['default_reorder_level']
        
        # Find books without stock records
        books_without_stock = Book.objects.filter(stock__isnull=True)
        created_count = 0
        
        for book in books_without_stock:
            stock, created = Stock.objects.get_or_create(
                book=book,
                defaults={
                    'quantity': default_quantity,
                    'reorder_level': default_reorder_level,
                    'max_stock_level': 100,
                    'reserved_quantity': 0,
                    'location_shelf': 'A1',
                    'location_row': '1',
                    'location_section': 'A'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created stock record for: {book.title}")
                
                # Update book status based on stock
                if stock.quantity == 0:
                    book.status = 'out_of_stock'
                    book.save(update_fields=['status'])
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} stock records')
        )