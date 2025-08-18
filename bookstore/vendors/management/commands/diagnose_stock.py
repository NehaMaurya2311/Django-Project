# management/commands/diagnose_stock.py
from django.core.management.base import BaseCommand
from django.db.models import F
from books.models import Book
from warehouse.models import Stock


class Command(BaseCommand):
    help = 'Diagnose stock issues and create missing stock records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually create missing stock records',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Check specific category only',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== STOCK DIAGNOSIS REPORT ===\n'))

        # Filter books
        books_query = Book.objects.all()
        if options['category']:
            books_query = books_query.filter(category__name__icontains=options['category'])

        total_books = books_query.count()
        self.stdout.write(f"Total books to check: {total_books}")

        # Check for books without stock records
        books_without_stock = books_query.filter(stock__isnull=True)
        missing_count = books_without_stock.count()

        self.stdout.write(f"\n📊 MISSING STOCK RECORDS: {missing_count}")
        if missing_count > 0:
            self.stdout.write("Books without stock records:")
            for book in books_without_stock[:10]:  # Show first 10
                self.stdout.write(f"  - {book.title} (Status: {book.status}, Category: {book.category.name})")

            if missing_count > 10:
                self.stdout.write(f"  ... and {missing_count - 10} more")

        # Check out-of-stock books
        out_of_stock = Stock.objects.filter(quantity=0)
        out_of_stock_count = out_of_stock.count()

        self.stdout.write(f"\n📉 OUT OF STOCK: {out_of_stock_count}")
        if out_of_stock_count > 0:
            self.stdout.write("Books with zero stock:")
            for stock in out_of_stock[:10]:
                self.stdout.write(f"  - {stock.book.title} (Book Status: {stock.book.status})")

            if out_of_stock_count > 10:
                self.stdout.write(f"  ... and {out_of_stock_count - 10} more")

        # Check low stock books
        low_stock = Stock.objects.filter(
            quantity__lte=F('reorder_level'),
            quantity__gt=0
        )
        low_stock_count = low_stock.count()

        self.stdout.write(f"\n⚠️  LOW STOCK: {low_stock_count}")
        if low_stock_count > 0:
            self.stdout.write("Books with low stock:")
            for stock in low_stock[:10]:
                self.stdout.write(
                    f"  - {stock.book.title} (Current: {stock.quantity}, Reorder: {stock.reorder_level})"
                )

        # Check book status consistency
        status_issues = []

        # Books marked as out_of_stock but have stock
        books_with_wrong_status = Book.objects.filter(
            status='out_of_stock',
            stock__quantity__gt=0
        )
        if books_with_wrong_status.exists():
            status_issues.append(
                f"Books marked 'out_of_stock' but have stock: {books_with_wrong_status.count()}"
            )

        # Books marked as available but out of stock
        books_available_but_no_stock = Book.objects.filter(
            status='available',
            stock__quantity=0
        )
        if books_available_but_no_stock.exists():
            status_issues.append(
                f"Books marked 'available' but out of stock: {books_available_but_no_stock.count()}"
            )

        if status_issues:
            self.stdout.write(f"\n🔧 STATUS INCONSISTENCIES:")
            for issue in status_issues:
                self.stdout.write(f"  - {issue}")

        # Summary
        total_needing_attention = missing_count + out_of_stock_count + low_stock_count
        self.stdout.write(f"\n📋 SUMMARY:")
        self.stdout.write(f"Total books needing vendor attention: {total_needing_attention}")
        self.stdout.write(f"High priority (out of stock/missing): {missing_count + out_of_stock_count}")
        self.stdout.write(f"Medium priority (low stock): {low_stock_count}")

        # Fix option
        if options['fix']:
            self.stdout.write(f"\n🔧 FIXING ISSUES...")

            # Create missing stock records
            created_count = 0
            for book in books_without_stock:
                Stock.objects.create(
                    book=book,
                    quantity=0,
                    reorder_level=10,
                    max_stock_level=100
                )
                created_count += 1

            self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} missing stock records."))

        self.stdout.write(self.style.SUCCESS("\n=== STOCK DIAGNOSIS COMPLETE ==="))
