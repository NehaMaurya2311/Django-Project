# support/views.py (Updated sections)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
import json
import logging

from .models import (
    SupportTicket, TicketResponse, SupportCategory, 
    LiveChat, ChatMessage, FAQ, FAQCategory
)
from .forms import (
    SupportTicketForm, TicketResponseForm, TicketFilterForm, 
    AdminTicketResponseForm, TicketRatingForm
)
from .chatbot import SupportChatbot

# Set up logging
logger = logging.getLogger(__name__)
from django.contrib.admin.views.decorators import staff_member_required
from .forms import TicketFilterForm, AdminTicketResponseForm, TicketRatingForm


def support_home(request):
    """
    Support center home page showing overview and quick access to support features
    """
    try:
        context = {}
        
        # Get popular FAQs (limit to 5)
        popular_faqs = FAQ.objects.filter(is_active=True).order_by('order')[:5]
        context['popular_faqs'] = popular_faqs
        
        # If user is authenticated, get their recent tickets
        if request.user.is_authenticated:
            recent_tickets = SupportTicket.objects.filter(
                user=request.user
            ).order_by('-created_at')[:5]
            context['recent_tickets'] = recent_tickets
        
        return render(request, 'support/support_home.html', context)
        
    except Exception as e:
        logger.error(f"Error in support_home view: {str(e)}")
        messages.error(request, 'There was an error loading the support center.')
        return render(request, 'support/support_home.html', {
            'popular_faqs': [],
            'recent_tickets': []
        })


@login_required
def rate_ticket(request, ticket_id):
    """Allow customers to rate resolved tickets"""
    try:
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
        
        # Only allow rating if ticket is resolved or closed
        if ticket.status not in ['resolved', 'closed']:
            messages.error(request, 'You can only rate tickets that have been resolved.')
            return redirect('support:ticket_detail', ticket_id=ticket_id)
        
        # Check if already rated
        if ticket.rating:
            messages.info(request, 'You have already rated this ticket.')
            return redirect('support:ticket_detail', ticket_id=ticket_id)
        
        if request.method == 'POST':
            form = TicketRatingForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save()
                messages.success(request, 'Thank you for your feedback!')
                logger.info(f"Ticket {ticket_id} rated by user {request.user.id}")
                return redirect('support:ticket_detail', ticket_id=ticket_id)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = TicketRatingForm(instance=ticket)
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        
        return render(request, 'support/rate_ticket.html', context)
        
    except Exception as e:
        logger.error(f"Error in rate_ticket view: {str(e)}")
        messages.error(request, 'There was an error loading the rating form.')
        return redirect('support:my_tickets')

# Live Chat Views
@login_required
def start_chat(request):
    """Start a new live chat session"""
    try:
        # Check if user already has an active chat
        existing_chat = LiveChat.objects.filter(
            user=request.user, 
            status__in=['waiting', 'active']
        ).first()
        
        if existing_chat:
            return redirect('support:chat_room', session_id=existing_chat.session_id)
        
        # Create new chat session
        chat = LiveChat.objects.create(user=request.user)
        logger.info(f"New chat session started: {chat.session_id} by user {request.user.id}")
        
        return redirect('support:chat_room', session_id=chat.session_id)
        
    except Exception as e:
        logger.error(f"Error starting chat: {str(e)}")
        messages.error(request, 'There was an error starting the chat session.')
        return redirect('support:my_tickets')

@login_required
def chat_room(request, session_id):
    """Display chat room interface"""
    try:
        chat = get_object_or_404(LiveChat, session_id=session_id)
        
        # Check permissions
        if not (request.user == chat.user or 
                (request.user.is_staff and chat.agent == request.user)):
            messages.error(request, 'You do not have permission to view this chat.')
            return redirect('support:my_tickets')
        
        context = {
            'chat': chat,
            'is_agent': request.user.is_staff and request.user == chat.agent
        }
        
        return render(request, 'support/chat_room.html', context)
        
    except Exception as e:
        logger.error(f"Error in chat_room view: {str(e)}")
        messages.error(request, 'There was an error loading the chat room.')
        return redirect('support:my_tickets')

@require_POST
@login_required
def send_message(request, session_id):
    """Send a message in chat"""
    try:
        chat = get_object_or_404(LiveChat, session_id=session_id)
        
        # Check permissions
        if not (request.user == chat.user or 
                (request.user.is_staff and chat.agent == request.user)):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Create message
        message = ChatMessage.objects.create(
            chat=chat,
            user=request.user,
            message=message_text,
            is_agent=request.user.is_staff
        )
        
        # Update chat status if needed
        if chat.status == 'waiting' and request.user.is_staff:
            chat.status = 'active'
            chat.agent = request.user
            chat.save()
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'message': message.message,
                'user': message.user.username,
                'is_agent': message.is_agent,
                'timestamp': message.timestamp.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return JsonResponse({'error': 'Error sending message'}, status=500)

@login_required
def get_messages(request, session_id):
    """Get chat messages (AJAX)"""
    try:
        chat = get_object_or_404(LiveChat, session_id=session_id)
        
        # Check permissions
        if not (request.user == chat.user or 
                (request.user.is_staff and chat.agent == request.user)):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        since_id = request.GET.get('since', 0)
        messages_qs = chat.messages.filter(id__gt=since_id).order_by('timestamp')
        
        messages_data = []
        for msg in messages_qs:
            messages_data.append({
                'id': msg.id,
                'message': msg.message,
                'user': msg.user.username,
                'is_agent': msg.is_agent,
                'timestamp': msg.timestamp.isoformat()
            })
        
        return JsonResponse({
            'messages': messages_data,
            'chat_status': chat.status
        })
        
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return JsonResponse({'error': 'Error retrieving messages'}, status=500)

@require_POST
@login_required
def end_chat(request, session_id):
    """End chat session"""
    try:
        chat = get_object_or_404(LiveChat, session_id=session_id)
        
        # Check permissions
        if not (request.user == chat.user or 
                (request.user.is_staff and chat.agent == request.user)):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        chat.status = 'ended'
        chat.ended_at = timezone.now()
        chat.save()
        
        logger.info(f"Chat session ended: {session_id} by user {request.user.id}")
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error ending chat: {str(e)}")
        return JsonResponse({'error': 'Error ending chat'}, status=500)

# Admin Views
@staff_member_required
def admin_tickets(request):
    """Admin view for managing support tickets"""
    try:
        tickets_list = SupportTicket.objects.all().select_related(
            'user', 'category', 'assigned_to'
        ).order_by('-created_at')
        
        # Apply filters
        filter_form = TicketFilterForm(request.GET)
        if filter_form.is_valid():
            if filter_form.cleaned_data['status']:
                tickets_list = tickets_list.filter(status=filter_form.cleaned_data['status'])
            if filter_form.cleaned_data['priority']:
                tickets_list = tickets_list.filter(priority=filter_form.cleaned_data['priority'])
            if filter_form.cleaned_data['category']:
                tickets_list = tickets_list.filter(category=filter_form.cleaned_data['category'])
        
        # Search functionality
        search_query = request.GET.get('search')
        if search_query:
            tickets_list = tickets_list.filter(
                Q(ticket_id__icontains=search_query) |
                Q(subject__icontains=search_query) |
                Q(user__username__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        paginator = Paginator(tickets_list, 20)
        page_number = request.GET.get('page')
        tickets = paginator.get_page(page_number)
        
        context = {
            'tickets': tickets,
            'filter_form': filter_form,
            'search_query': search_query,
        }
        
        return render(request, 'support/admin_tickets.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_tickets view: {str(e)}")
        messages.error(request, 'There was an error loading the tickets.')
        return render(request, 'support/admin_tickets.html', {'tickets': None})

@staff_member_required
def admin_ticket_detail(request, ticket_id):
    """Admin view for ticket details with response capability"""
    try:
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
        
        if request.method == 'POST':
            form = AdminTicketResponseForm(request.POST, request.FILES)
            if form.is_valid():
                # Create response
                response = TicketResponse.objects.create(
                    ticket=ticket,
                    user=request.user,
                    message=form.cleaned_data['message'],
                    attachment=form.cleaned_data.get('attachment'),
                    is_internal=form.cleaned_data.get('is_internal', False)
                )
                
                # Update ticket status if specified
                new_status = form.cleaned_data.get('new_status')
                if new_status:
                    old_status = ticket.status
                    ticket.status = new_status
                    if new_status == 'resolved':
                        ticket.resolved_at = timezone.now()
                    
                    logger.info(f"Ticket {ticket_id} status changed from {old_status} to {new_status} by admin {request.user.id}")
                
                # Assign ticket to current admin if not assigned
                if not ticket.assigned_to:
                    ticket.assigned_to = request.user
                
                ticket.updated_at = timezone.now()
                ticket.save()
                
                messages.success(request, 'Response added successfully.')
                return redirect('support:admin_ticket_detail', ticket_id=ticket_id)
            else:
                messages.error(request, 'Please correct the errors in your response.')
        else:
            form = AdminTicketResponseForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        
        return render(request, 'support/admin_ticket_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_ticket_detail view: {str(e)}")
        messages.error(request, 'There was an error loading the ticket details.')
        return redirect('support:admin_tickets')

@staff_member_required
def admin_live_chats(request):
    """Admin view for managing live chats"""
    try:
        chats_list = LiveChat.objects.all().select_related('user', 'agent').order_by('-started_at')
        
        # Filter by status
        status_filter = request.GET.get('status')
        if status_filter and status_filter in dict(LiveChat.CHAT_STATUS):
            chats_list = chats_list.filter(status=status_filter)
        
        paginator = Paginator(chats_list, 20)
        page_number = request.GET.get('page')
        chats = paginator.get_page(page_number)
        
        context = {
            'chats': chats,
            'status_choices': LiveChat.CHAT_STATUS,
            'current_status': status_filter
        }
        
        return render(request, 'support/admin_live_chats.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_live_chats view: {str(e)}")
        messages.error(request, 'There was an error loading the chat sessions.')
        return render(request, 'support/admin_live_chats.html', {'chats': None})

@staff_member_required
def admin_join_chat(request, session_id):
    """Allow admin to join/take over a chat session"""
    try:
        chat = get_object_or_404(LiveChat, session_id=session_id)
        
        # Assign agent and update status
        if chat.status == 'waiting':
            chat.agent = request.user
            chat.status = 'active'
            chat.save()
            
            # Send system message
            ChatMessage.objects.create(
                chat=chat,
                user=request.user,
                message=f"Agent {request.user.username} has joined the chat.",
                is_agent=True
            )
            
            logger.info(f"Admin {request.user.id} joined chat {session_id}")
        
        return redirect('support:chat_room', session_id=session_id)
        
    except Exception as e:
        logger.error(f"Error in admin_join_chat view: {str(e)}")
        messages.error(request, 'There was an error joining the chat.')
        return redirect('support:admin_live_chats')

def faq(request):
    """Display FAQ page with categories and questions"""
    try:
        # Get all FAQ categories and their questions
        categories = FAQCategory.objects.filter(is_active=True).prefetch_related('faqs').order_by('order', 'name')
        
        # Group FAQs by category
        faq_by_category = {}
        total_faqs = 0
        
        for category in categories:
            active_faqs = category.faqs.filter(is_active=True).order_by('order', 'question')
            if active_faqs.exists():
                faq_by_category[category] = active_faqs
                total_faqs += active_faqs.count()
        
        context = {
            'faq_by_category': faq_by_category,
            'total_faqs': total_faqs,
        }
        
        return render(request, 'support/faq.html', context)
    except Exception as e:
        logger.error(f"Error in FAQ view: {str(e)}")
        messages.error(request, 'There was an error loading the FAQ page.')
        return render(request, 'support/faq.html', {'faq_by_category': {}, 'total_faqs': 0})

@login_required
def create_ticket(request):
    """Create a new support ticket"""
    if request.method == 'POST':
        form = SupportTicketForm(user=request.user, data=request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            messages.success(request, f'Support ticket #{ticket.ticket_id} created successfully!')
            return redirect('support:ticket_detail', ticket_id=ticket.ticket_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SupportTicketForm(user=request.user)
    
    return render(request, 'support/create_ticket.html', {'form': form})

@login_required
def my_tickets(request):
    """Display user's support tickets"""
    try:
        tickets_list = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
        
        status_filter = request.GET.get('status')
        if status_filter and status_filter in dict(SupportTicket.TICKET_STATUS):
            tickets_list = tickets_list.filter(status=status_filter)
        
        paginator = Paginator(tickets_list, 10)
        page_number = request.GET.get('page')
        tickets = paginator.get_page(page_number)
        
        context = {
            'tickets': tickets,
            'status_choices': SupportTicket.TICKET_STATUS,
            'current_status': status_filter
        }
        
        return render(request, 'support/my_tickets.html', context)
    except Exception as e:
        logger.error(f"Error in my_tickets view: {str(e)}")
        messages.error(request, 'There was an error loading your tickets.')
        return render(request, 'support/my_tickets.html', {'tickets': None})

class ChatbotView(View):
    """Enhanced chatbot view with better error handling"""
    
    def __init__(self):
        super().__init__()
        self.chatbot = SupportChatbot()
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        try:
            # Parse JSON data
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON data'
                }, status=400)
            
            message = data.get('message', '').strip()
            
            if not message:
                return JsonResponse({
                    'error': 'Message cannot be empty'
                }, status=400)
            
            # Get user context
            user = request.user if request.user.is_authenticated else None
            
            # Get chatbot response
            response = self.chatbot.get_response(message, user)
            
            # Log the interaction
            logger.info(f"Chatbot interaction - User: {user.id if user else 'Anonymous'}, Message: {message[:100]}...")
            
            return JsonResponse({
                'response': response,
                'timestamp': timezone.now().isoformat(),
                'user_authenticated': user is not None
            })
            
        except Exception as e:
            logger.error(f"Error in ChatbotView: {str(e)}")
            return JsonResponse({
                'error': 'An error occurred processing your request',
                'response': {
                    'message': "I'm sorry, I encountered an error. Please try again or contact our support team if the problem persists.",
                    'type': 'text',
                    'suggestions': ['Try Again', 'Contact Support', 'View FAQ']
                }
            }, status=500)
    
    def get(self, request):
        """Handle GET requests - redirect to chatbot widget"""
        return redirect('support:chatbot_widget')

@require_POST
@login_required
def create_ticket_from_chatbot(request):
    """Create support ticket from chatbot interaction"""
    try:
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data'
            }, status=400)
        
        category_id = data.get('category_id')
        subject = data.get('subject', '').strip()
        description = data.get('description', '').strip()
        
        # Validate required fields
        if not category_id:
            return JsonResponse({
                'success': False,
                'message': 'Please select a category'
            })
        
        if not subject:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a subject'
            })
        
        if not description:
            return JsonResponse({
                'success': False,
                'message': 'Please provide a description'
            })
        
        # Create ticket using chatbot helper
        chatbot = SupportChatbot()
        result = chatbot.create_ticket_from_chat(
            request.user, category_id, subject, description
        )
        
        # Log ticket creation
        if result.get('success'):
            logger.info(f"Ticket created via chatbot - User: {request.user.id}, Ticket: {result.get('ticket_id')}")
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error creating ticket from chatbot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred creating your ticket. Please try again or use the regular ticket creation form.'
        })

def chatbot_widget(request):
    """Render the chatbot widget/interface"""
    try:
        # Get some initial data that might be useful
        categories = SupportCategory.objects.filter(is_active=True).order_by('name')
        popular_faqs = FAQ.objects.filter(is_active=True).order_by('order')[:5]
        
        context = {
            'categories': categories,
            'popular_faqs': popular_faqs,
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, 'support/chatbot_widget.html', context)
    except Exception as e:
        logger.error(f"Error in chatbot_widget view: {str(e)}")
        return render(request, 'support/chatbot_widget.html', {
            'categories': [],
            'popular_faqs': [],
            'user_authenticated': False
        })

# Enhanced ticket detail view
@login_required
def ticket_detail(request, ticket_id):
    """Display ticket details and handle responses"""
    try:
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
        
        if request.method == 'POST':
            form = TicketResponseForm(request.POST, request.FILES)
            if form.is_valid():
                # Create the response
                response = TicketResponse.objects.create(
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
                logger.info(f"Response added to ticket {ticket_id} by user {request.user.id}")
                
                return redirect('support:ticket_detail', ticket_id=ticket_id)
            else:
                messages.error(request, 'Please correct the errors in your response.')
        else:
            form = TicketResponseForm()
        
        context = {
            'ticket': ticket,
            'form': form,
        }
        
        return render(request, 'support/ticket_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in ticket_detail view: {str(e)}")
        messages.error(request, 'There was an error loading the ticket details.')
        return redirect('support:my_tickets')

# Helper function to validate chatbot responses
def validate_chatbot_response(response):
    """Validate chatbot response structure"""
    required_fields = ['message', 'type']
    
    if not isinstance(response, dict):
        return False
    
    for field in required_fields:
        if field not in response:
            return False
    
    return True