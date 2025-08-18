# vendors/management/commands/fix_deliveries.py
from django.core.management.base import BaseCommand
from logistics.models import DeliverySchedule, DeliveryTracking
from vendors.models import StockOffer

class Command(BaseCommand):
    help = "Ensure all deliveries have at least one tracking update."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving changes (preview only)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        deliveries = DeliverySchedule.objects.all()
        self.stdout.write(f"Found {deliveries.count()} delivery schedules")

        for delivery in deliveries:
            self.stdout.write(f"Delivery #{delivery.id}: {delivery.status}")

            # Ensure tracking exists
            if not delivery.tracking_updates.exists():
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  - Would create initial tracking for delivery #{delivery.id}"
                        )
                    )
                else:
                    DeliveryTracking.objects.create(
                        delivery=delivery,
                        status=delivery.status,
                        notes=f"Initial tracking created for delivery #{delivery.id}",
                        updated_by_id=1  # Use admin user
                    )
                    self.stdout.write(self.style.SUCCESS(f"  - Created initial tracking"))

        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry run complete. No changes saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Fix deliveries completed."))
