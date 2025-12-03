# support/chatbot.py - Updated with correct URL mappings
import re
from django.utils import timezone
from django.urls import reverse
from .models import FAQ, SupportTicket, SupportCategory

class SupportChatbot:
    def __init__(self):
        self.intents = {
            'greeting': {
                'patterns': [
                    r'\b(hi|hello|hey|good\s+(morning|afternoon|evening))\b',
                    r'\bhelp\b'
                ],
                'responses': [
                    "Hi! I'm here to help you. What can I assist you with today?",
                    "Hello! How can I help you with your support needs?",
                    "Hey there! I'm your support assistant. What do you need help with?"
                ]
            },
            'faq': {
                'patterns': [
                    r'\b(faq|frequently\s+asked|common\s+questions|view\s+faq)\b',
                    r'\bquestions?\b'
                ],
                'responses': [
                    "Here are some frequently asked questions that might help you:",
                ]
            },
            'order_status': {
                'patterns': [
                    r'\b(order|purchase|buy|bought)\b.*\b(status|track|where|when)\b',
                    r'\btrack.*order\b',
                    r'\border.*status\b',
                    r'\bcheck\s+order\s+status\b'
                ],
                'responses': [
                    "I can help you with order-related questions. You can check your order status in your account dashboard, or I can create a support ticket for you if you need specific assistance."
                ]
            },
            'account_dashboard': {
                'patterns': [
                    r'\b(account\s+dashboard|dashboard|my\s+account)\b',
                    r'\bcheck\s+account\s+dashboard\b',
                    r'\bgo\s+to\s+(account|dashboard)\b'
                ],
                'responses': [
                    "I can help you navigate to your account dashboard where you can view your orders, profile, and more."
                ]
            },
            'login': {
                'patterns': [
                    r'\b(login|log\s+in|sign\s+in)\b',
                    r'\bneed\s+to\s+login\b'
                ],
                'responses': [
                    "I can help you with login-related issues. You can access the login page to sign in to your account."
                ]
            },
            'register': {
                'patterns': [
                    r'\b(register|sign\s+up|create\s+account|new\s+account)\b',
                    r'\bneed\s+to\s+register\b'
                ],
                'responses': [
                    "I can help you create a new account. You can access the registration page to get started."
                ]
            },
            'refund': {
                'patterns': [
                    r'\b(refund|return|money\s+back|cancel.*order)\b',
                    r'\bget.*money\s+back\b'
                ],
                'responses': [
                    "For refund requests, I'll need to create a support ticket for you so our team can review your specific case. Would you like me to help you create one?"
                ]
            },
            'technical_issue': {
                'patterns': [
                    r'\b(bug|error|problem|issue|not\s+working|broken)\b',
                    r'\bcan\'?t\s+(login|access|use)\b',
                    r'\btechnical\s+issue\b'
                ],
                'responses': [
                    "I'm sorry you're experiencing technical difficulties. Let me help you create a support ticket so our technical team can assist you properly."
                ]
            },
            'create_ticket': {
                'patterns': [
                    r'\b(create|open|submit).*ticket\b',
                    r'\bticket\b',
                    r'\bspeak.*human\b',
                    r'\btalk.*agent\b',
                    r'\bhuman\s+agent\b'
                ],
                'responses': [
                    "I can help you create a support ticket. This will connect you with our human support team for personalized assistance."
                ]
            },
            'goodbye': {
                'patterns': [
                    r'\b(bye|goodbye|see\s+you|thanks?|thank\s+you)\b',
                    r'\bthat\'?s\s+all\b'
                ],
                'responses': [
                    "You're welcome! Feel free to ask if you need any more help.",
                    "Goodbye! Don't hesitate to reach out if you have more questions.",
                    "Thanks for chatting! I'm here whenever you need support."
                ]
            }
        }
    
    def get_response(self, message, user=None):
        """Process user message and return appropriate response"""
        message_lower = message.lower().strip()
        
        # Check for intent matches
        for intent, data in self.intents.items():
            for pattern in data['patterns']:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    return self._handle_intent(intent, message, user)
        
        # If no intent matched, try FAQ search
        faq_response = self._search_faq(message)
        if faq_response:
            return faq_response
        
        # Default response
        return {
            'message': "I'm not sure I understand. Could you rephrase your question? You can also create a support ticket for human assistance, or check our FAQ section.",
            'type': 'text',
            'suggestions': ['Create Support Ticket', 'View FAQ', 'Talk to Human Agent']
        }
    
    def _handle_intent(self, intent, message, user):
        """Handle specific intents"""
        import random
        
        if intent == 'greeting':
            return {
                'message': random.choice(self.intents[intent]['responses']),
                'type': 'text',
                'suggestions': ['Check Order Status', 'Technical Issue', 'Refund Request', 'View FAQ']
            }
        
        elif intent == 'faq':
            faqs = self._get_popular_faqs()
            return {
                'message': self.intents[intent]['responses'][0],
                'type': 'faq_list',
                'data': faqs,
                'suggestions': ['Create Support Ticket', 'More Questions'],
                'action': {
                    'type': 'navigate',
                    'url': reverse('support:faq'),
                    'text': 'View Full FAQ Page'
                }
            }
        
        elif intent == 'order_status':
            if user and user.is_authenticated:
                return {
                    'message': self.intents[intent]['responses'][0],
                    'type': 'text',
                    'suggestions': ['Create Support Ticket', 'Go to Account Dashboard'],
                    'action': {
                        'type': 'navigate',
                        'url': reverse('orders:order_list'),  # Updated to use orders:order_list
                        'text': 'View My Orders'
                    }
                }
            else:
                return {
                    'message': "To check your order status, please log in first. If you don't have an account, you can create one.",
                    'type': 'text',
                    'suggestions': ['Login', 'Create Account', 'Continue as Guest'],
                    'actions': [
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:login'),
                            'text': 'Login'
                        },
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:signup'),
                            'text': 'Create Account'
                        }
                    ]
                }
        
        elif intent == 'account_dashboard':
            if user and user.is_authenticated:
                return {
                    'message': "You can access your account dashboard to view your orders, update your profile, and manage your account settings.",
                    'type': 'text',
                    'suggestions': ['View Orders', 'View Profile', 'Need More Help'],
                    'actions': [
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:dashboard'),
                            'text': 'Go to Dashboard'
                        },
                        {
                            'type': 'navigate',
                            'url': reverse('orders:order_list'),
                            'text': 'View My Orders'
                        },
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:profile'),
                            'text': 'View Profile'
                        }
                    ]
                }
            else:
                return {
                    'message': "To access your account dashboard, please log in first. If you don't have an account, you can create one.",
                    'type': 'text',
                    'suggestions': ['Login', 'Create Account', 'Continue as Guest'],
                    'actions': [
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:login'),
                            'text': 'Login'
                        },
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:signup'),
                            'text': 'Create Account'
                        }
                    ]
                }
        
        elif intent == 'login':
            return {
                'message': "I can help you access the login page. If you're having trouble logging in, I can also create a support ticket for you.",
                'type': 'text',
                'suggestions': ['Go to Login Page', 'Forgot Password', 'Create Support Ticket'],
                'actions': [
                    {
                        'type': 'navigate',
                        'url': reverse('accounts:login'),
                        'text': 'Go to Login Page'
                    },
                    {
                        'type': 'navigate',
                        'url': reverse('accounts:password_reset'),
                        'text': 'Reset Password'
                    }
                ]
            }
        
        elif intent == 'register':
            return {
                'message': "I can help you create a new account. Click below to go to the registration page.",
                'type': 'text',
                'suggestions': ['Go to Registration', 'Already Have Account', 'Need Help'],
                'action': {
                    'type': 'navigate',
                    'url': reverse('accounts:signup'),
                    'text': 'Create New Account'
                }
            }
        
        elif intent == 'refund':
            return {
                'message': self.intents[intent]['responses'][0],
                'type': 'text',
                'suggestions': ['Yes, Create Ticket', 'Cancel', 'View Refund Policy']
            }
        
        elif intent == 'technical_issue':
            return {
                'message': self.intents[intent]['responses'][0],
                'type': 'text',
                'suggestions': ['Create Technical Support Ticket', 'View FAQ', 'Try Common Solutions']
            }
        
        elif intent == 'create_ticket':
            if user and user.is_authenticated:
                categories = SupportCategory.objects.filter(is_active=True)
                return {
                    'message': "What type of issue would you like to report?",
                    'type': 'ticket_categories',
                    'data': [{'id': cat.id, 'name': cat.name} for cat in categories]
                }
            else:
                return {
                    'message': "To create a support ticket, please log in to your account first.",
                    'type': 'text',
                    'suggestions': ['Login', 'Register'],
                    'actions': [
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:login'),
                            'text': 'Login'
                        },
                        {
                            'type': 'navigate',
                            'url': reverse('accounts:signup'),
                            'text': 'Register'
                        }
                    ]
                }
        
        elif intent == 'goodbye':
            return {
                'message': random.choice(self.intents[intent]['responses']),
                'type': 'text'
            }
        
        return {
            'message': random.choice(self.intents[intent]['responses']),
            'type': 'text'
        }
    
    def _search_faq(self, query):
        """Search FAQ for relevant answers"""
        query_terms = query.lower().split()
        
        # Simple keyword matching in FAQ questions and answers
        faqs = FAQ.objects.filter(is_active=True)
        scored_faqs = []
        
        for faq in faqs:
            score = 0
            faq_text = f"{faq.question} {faq.answer}".lower()
            
            for term in query_terms:
                if len(term) > 2:  # Skip very short terms
                    if term in faq_text:
                        score += faq_text.count(term)
            
            if score > 0:
                scored_faqs.append((faq, score))
        
        # Sort by relevance score and return top matches
        scored_faqs.sort(key=lambda x: x[1], reverse=True)
        
        if scored_faqs:
            top_faqs = [faq for faq, score in scored_faqs[:3]]
            return {
                'message': "I found some relevant information in our FAQ:",
                'type': 'faq_results',
                'data': [{'question': faq.question, 'answer': faq.answer} for faq in top_faqs],
                'suggestions': ['More Help Needed', 'Create Support Ticket'],
                'action': {
                    'type': 'navigate',
                    'url': reverse('support:faq'),
                    'text': 'View Full FAQ Page'
                }
            }
        
        return None
    
    def _get_popular_faqs(self, limit=5):
        """Get popular/featured FAQs"""
        faqs = FAQ.objects.filter(is_active=True).order_by('order', 'question')[:limit]
        return [{'question': faq.question, 'answer': faq.answer} for faq in faqs]
    
    def create_ticket_from_chat(self, user, category_id, subject, description):
        """Helper method to create support ticket from chatbot interaction"""
        try:
            category = SupportCategory.objects.get(id=category_id, is_active=True)
            ticket = SupportTicket.objects.create(
                user=user,
                category=category,
                subject=subject or "Support Request via Chatbot",
                description=description,
                priority='medium'
            )
            return {
                'success': True,
                'ticket_id': ticket.ticket_id,
                'message': f"Support ticket #{ticket.ticket_id} has been created successfully! Our team will get back to you soon.",
                'action': {
                    'type': 'navigate',
                    'url': reverse('support:ticket_detail', kwargs={'ticket_id': ticket.ticket_id}),
                    'text': 'View Ticket'
                }
            }
        except SupportCategory.DoesNotExist:
            return {
                'success': False,
                'message': "Invalid category selected. Please try again."
            }
        except Exception as e:
            return {
                'success': False,
                'message': "There was an error creating your ticket. Please try again later."
            }