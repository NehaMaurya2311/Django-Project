from .models import SupportTicket

def support_context(request):
    """Add support-related context variables"""
    context = {}
    
    if request.user.is_authenticated:
        # Unread tickets count (tickets with new responses from support)
        open_tickets_count = SupportTicket.objects.filter(
            user=request.user,
            status__in=['open', 'in_progress', 'waiting_customer']
        ).count()
        
        context['open_tickets_count'] = open_tickets_count
    
    return context