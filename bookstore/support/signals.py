# support/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import SupportTicket, TicketResponse

@receiver(post_save, sender=SupportTicket)
def ticket_created(sender, instance, created, **kwargs):
    """Send email notification when ticket is created"""
    if created:
        subject = f'Support Ticket Created: #{instance.ticket_id}'
        message = render_to_string('support/emails/ticket_created.txt', {
            'ticket': instance,
            'user': instance.user,
        })
        
        # Send to customer
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.user.email],
            fail_silently=True,
        )
        
        # Send to support team
        if hasattr(settings, 'SUPPORT_EMAIL'):
            send_mail(
                f'New Support Ticket: #{instance.ticket_id}',
                f'A new support ticket has been created by {instance.user.username}.\n\n'
                f'Subject: {instance.subject}\n'
                f'Priority: {instance.get_priority_display()}\n'
                f'Category: {instance.category}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.SUPPORT_EMAIL],
                fail_silently=True,
            )

@receiver(post_save, sender=TicketResponse)
def response_added(sender, instance, created, **kwargs):
    """Send email notification when response is added"""
    if created and not instance.is_internal:
        ticket = instance.ticket
        
        # Determine recipient (customer or agent)
        if instance.user == ticket.user:
            # Customer replied, notify assigned agent
            if ticket.assigned_to and ticket.assigned_to.email:
                subject = f'Customer Reply: #{ticket.ticket_id}'
                recipient = ticket.assigned_to.email
        else:
            # Agent replied, notify customer
            subject = f'Support Update: #{ticket.ticket_id}'
            recipient = ticket.user.email
        
        if 'recipient' in locals():
            message = render_to_string('support/emails/response_added.txt', {
                'ticket': ticket,
                'response': instance,
            })
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=True,
            )

