# logistics/management/commands/fix_orphaned_deliveries.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from logistics.models import DeliverySchedule, StockReceiptConfirmation, DeliveryTracking
from vendors.models import OfferStatusNotification

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix deliveries that updated stock but have no StockReceiptConfirmation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            dest='user_id',
            help='Staff user ID to assign as the confirmer (required for actual run)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_id = options.get('user_id')
        
        if not dry_run and not user_id:
            self.stdout.write(
                self.style.ERROR('--user-id is required when not doing a dry run')
            )
            return
        
        # Find deliveries that have updated stock but no confirmation
        orphaned_deliveries = DeliverySchedule.objects.filter(
            stock_offer__status='processed',
            stock_offer__is_delivered=True,
            status='arrived'  # Still showing as arrived but stock was processed
        ).exclude(
            id__in=StockReceiptConfirmation.objects.values_list('delivery_schedule_id', flat=True)
        ).select_related('vendor', 'stock_offer__book')
        
        if not orphaned_deliveries.exists():
            self.stdout.write(
                self.style.SUCCESS('No orphaned deliveries found. All good!')
            )
            return
        
        self.stdout.write(
            f'Found {orphaned_deliveries.count()} orphaned deliveries:'
        )
        
        for delivery in orphaned_deliveries:
            self.stdout.write(
                f'  - Delivery #{delivery.id}: {delivery.stock_offer.book.title} '
                f'({delivery.stock_offer.quantity} books from {delivery.vendor.business_name})'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: No changes made. Use without --dry-run to fix.')
            )
            return
        
        # Get the staff user
        try:
            staff_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with ID {user_id} not found')
            )
            return
        
        # Fix each orphaned delivery
        fixed_count = 0
        for delivery in orphaned_deliveries:
            try:
                # Create the missing StockReceiptConfirmation
                confirmation = StockReceiptConfirmation.objects.create(
                    delivery_schedule=delivery,
                    received_by_staff=staff_user,
                    books_received=delivery.stock_offer.quantity,
                    books_accepted=delivery.stock_offer.delivered_quantity or delivery.stock_offer.quantity,
                    books_rejected=0,
                    rejection_reason='',
                    condition_rating=5,  # Assume good condition since stock was accepted
                    quality_notes='Auto-created confirmation for previously processed delivery',
                    stock_updated=True,
                    stock_movement_created=True,
                )
                
                # Update delivery status properly
                delivery.status = 'completed'
                delivery.verified_quantity = confirmation.books_accepted
                if not delivery.completed_at:
                    delivery.completed_at = timezone.now()
                delivery.save()
                
                # Create tracking updates to show the progression
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='verified',
                    notes=f"Stock verified (auto-created confirmation for previously processed delivery)",
                    updated_by=staff_user
                )
                
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='completed',
                    notes=f"Delivery marked as completed. Stock was already updated in warehouse.",
                    updated_by=staff_user
                )
                
                # Make sure stock offer has proper confirmation fields
                if not delivery.stock_offer.staff_confirmed_by:
                    delivery.stock_offer.staff_confirmed_by = staff_user
                if not delivery.stock_offer.staff_confirmed_at:
                    delivery.stock_offer.staff_confirmed_at = timezone.now()
                delivery.stock_offer.save()
                
                # Create completion notification if none exists
                existing_notification = OfferStatusNotification.objects.filter(
                    stock_offer=delivery.stock_offer,
                    status='completed'
                ).first()
                
                if not existing_notification:
                    OfferStatusNotification.objects.create(
                        stock_offer=delivery.stock_offer,
                        status='completed',
                        message=f"Stock confirmed! {confirmation.books_accepted} copies of '{delivery.stock_offer.book.title}' have been added to our inventory. Your offer is now complete."
                    )
                
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Fixed delivery #{delivery.id} - {delivery.stock_offer.book.title}'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error fixing delivery #{delivery.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully fixed {fixed_count} out of {orphaned_deliveries.count()} orphaned deliveries!'
            )
        )
        
        if fixed_count > 0:
            self.stdout.write(
                'These deliveries should now be cleared from the pending receipts list.'
            )