# support/views.py (continued)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import SupportTicket, TicketResponse, SupportCategory, LiveChat, ChatMessage
from .forms import SupportTicketForm, TicketResponseForm

@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = SupportTicketForm(user=request.user, data=request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            messages.success(request, f'Support ticket #{ticket.ticket_id} created successfully!')
            return redirect('support:ticket_detail', ticket_id=ticket.ticket_id)
    else:
        form = SupportTicketForm(user=request.user)
    
    return render(request, 'support/create_ticket.html', {'form': form})

@login_required
def my_tickets(request):
    tickets_list = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        tickets_list = tickets_list.filter(status=status_filter)
    
    paginator = Paginator(tickets_list, 10)
    page_number = request.GET.get('page')
    tickets = paginator.get_page(page_number)
    
    return render(request, 'support/my_tickets.html', {'tickets': tickets})

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
    
    if request.method == 'POST':
        form = TicketResponseForm(request.POST, request.FILES)
        if form.is_valid():
            TicketResponse.objects.create(
                ticket=ticket,
                user=request.user,
                message=form.cleaned_data['message'],
                attachment=form.cleaned_data.get('attachment')
            )
            
            # Update ticket status and timestamp
            if ticket.status == 'waiting_customer':
                ticket.status = 'in_progress'
            elif ticket.status == 'resolved':
                ticket.status = 'open'
            
            ticket.updated_at = timezone.now()
            ticket.save()
            
            messages.success(request, 'Your response has been added.')
            return redirect('support:ticket_detail', ticket_id=ticket_id)
    else:
        form = TicketResponseForm()
    
    context = {
        'ticket': ticket,
        'form': form,
    }
    
    return render(request, 'support/ticket_detail.html', context)

@login_required
def start_chat(request):
    # Check if user has an active chat
    active_chat = LiveChat.objects.filter(user=request.user, status__in=['waiting', 'active']).first()
    
    if active_chat:
        return redirect('support:chat_room', session_id=active_chat.session_id)
    
    # Create new chat session
    chat = LiveChat.objects.create(user=request.user)
    return redirect('support:chat_room', session_id=chat.session_id)

@login_required
def chat_room(request, session_id):
    chat = get_object_or_404(LiveChat, session_id=session_id, user=request.user)
    return render(request, 'support/chat_room.html', {'chat': chat})

@login_required
@require_POST
def send_message(request, session_id):
    chat = get_object_or_404(LiveChat, session_id=session_id, user=request.user)
    message_text = request.POST.get('message', '').strip()
    
    if message_text:
        ChatMessage.objects.create(
            chat=chat,
            user=request.user,
            message=message_text,
            is_agent=False
        )
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Empty message'})

@login_required
def get_messages(request, session_id):
    chat = get_object_or_404(LiveChat, session_id=session_id, user=request.user)
    messages = chat.messages.all()
    
    message_data = []
    for msg in messages:
        message_data.append({
            'user': msg.user.username,
            'message': msg.message,
            'is_agent': msg.is_agent,
            'timestamp': msg.timestamp.strftime('%H:%M')
        })
    
    return JsonResponse({'messages': message_data})

@login_required
@require_POST
def end_chat(request, session_id):
    chat = get_object_or_404(LiveChat, session_id=session_id, user=request.user)
    chat.status = 'ended'
    chat.ended_at = timezone.now()
    chat.save()
    
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def rate_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
    rating = request.POST.get('rating')
    feedback = request.POST.get('feedback', '')
    
    if rating and rating.isdigit() and 1 <= int(rating) <= 5:
        ticket.rating = int(rating)
        ticket.feedback = feedback
        ticket.save()
        
        messages.success(request, 'Thank you for your feedback!')
    else:
        messages.error(request, 'Please provide a valid rating (1-5).')
    
    return redirect('support:ticket_detail', ticket_id=ticket_id)

# Admin views
def is_support_staff(user):
    return user.is_staff or user.groups.filter(name='Support Team').exists()

@user_passes_test(is_support_staff)
def admin_tickets(request):
    tickets_list = SupportTicket.objects.all().order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    assigned_filter = request.GET.get('assigned')
    
    if status_filter:
        tickets_list = tickets_list.filter(status=status_filter)
    if priority_filter:
        tickets_list = tickets_list.filter(priority=priority_filter)
    if assigned_filter:
        if assigned_filter == 'unassigned':
            tickets_list = tickets_list.filter(assigned_to__isnull=True)
        else:
            tickets_list = tickets_list.filter(assigned_to__id=assigned_filter)
    
    paginator = Paginator(tickets_list, 20)
    page_number = request.GET.get('page')
    tickets = paginator.get_page(page_number)
    
    context = {
        'tickets': tickets,
        'status_choices': SupportTicket.TICKET_STATUS,
        'priority_choices': SupportTicket.PRIORITY_LEVELS,
    }
    
    return render(request, 'support/admin/tickets.html', context)

@user_passes_test(is_support_staff)
def admin_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'respond':
            form = TicketResponseForm(request.POST, request.FILES)
            if form.is_valid():
                response = TicketResponse.objects.create(
                    ticket=ticket,
                    user=request.user,
                    message=form.cleaned_data['message'],
                    attachment=form.cleaned_data.get('attachment'),
                    is_internal='internal' in request.POST
                )
                
                # Update ticket status
                new_status = request.POST.get('new_status')
                if new_status and new_status != ticket.status:
                    ticket.status = new_status
                    if new_status == 'resolved':
                        ticket.resolved_at = timezone.now()
                
                ticket.updated_at = timezone.now()
                ticket.save()
                
                messages.success(request, 'Response added successfully.')
                return redirect('support:admin_ticket_detail', ticket_id=ticket_id)
        
        elif action == 'update':
            ticket.status = request.POST.get('status', ticket.status)
            ticket.priority = request.POST.get('priority', ticket.priority)
            
            assigned_to_id = request.POST.get('assigned_to')
            if assigned_to_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    ticket.assigned_to = User.objects.get(id=assigned_to_id)
                except User.DoesNotExist:
                    pass
            
            ticket.save()
            messages.success(request, 'Ticket updated successfully.')
            return redirect('support:admin_ticket_detail', ticket_id=ticket_id)
    
    else:
        form = TicketResponseForm()
    
    context = {
        'ticket': ticket,
        'form': form,
        'status_choices': SupportTicket.TICKET_STATUS,
        'priority_choices': SupportTicket.PRIORITY_LEVELS,
    }
    
    return render(request, 'support/admin/ticket_detail.html', context)

@user_passes_test(is_support_staff)
def admin_live_chats(request):
    chats = LiveChat.objects.filter(status__in=['waiting', 'active']).order_by('-started_at')
    return render(request, 'support/admin/live_chats.html', {'chats': chats})

@user_passes_test(is_support_staff)
def admin_join_chat(request, session_id):
    chat = get_object_or_404(LiveChat, session_id=session_id)
    
    if chat.status == 'waiting':
        chat.agent = request.user
        chat.status = 'active'
        chat.save()
    
    return render(request, 'support/admin/chat_room.html', {'chat': chat})
