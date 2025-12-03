# support/management/commands/populate_faq.py
from django.core.management.base import BaseCommand
from django.db import transaction
from support.models import FAQCategory, FAQ


class Command(BaseCommand):
    help = 'Populate FAQ categories and questions for the support system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing FAQ data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing FAQ data...')
            FAQ.objects.all().delete()
            FAQCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing FAQ data cleared.'))

        with transaction.atomic():
            self.create_faq_data()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated FAQ database')
        )

    def create_faq_data(self):
        """Create FAQ categories and questions"""
        
        # Account & Authentication
        account_category = FAQCategory.objects.create(
            name="Account & Authentication",
            description="Questions about user accounts, login, registration, and password management",
            order=1
        )
        
        account_faqs = [
            {
                'question': 'How do I create a new account?',
                'answer': 'To create a new account, click on "Sign Up" or "Register" on our homepage. Fill in your email address, create a secure password, and provide the required information. You\'ll receive a confirmation email to verify your account.',
                'order': 1
            },
            {
                'question': 'I forgot my password. How can I reset it?',
                'answer': 'Click on "Forgot Password" on the login page. Enter your email address and we\'ll send you a password reset link. Follow the instructions in the email to create a new password. If you don\'t receive the email, check your spam folder.',
                'order': 2
            },
            {
                'question': 'Why can\'t I log into my account?',
                'answer': 'Common login issues include: incorrect email/password combination, account not yet verified, or account temporarily locked. Try resetting your password, check for verification emails, or wait a few minutes if you\'ve had multiple failed attempts.',
                'order': 3
            },
            {
                'question': 'How do I change my email address?',
                'answer': 'Log into your account and go to "Account Settings" or "Profile". Update your email address and click "Save". You may need to verify the new email address before the change takes effect.',
                'order': 4
            },
            {
                'question': 'Can I delete my account permanently?',
                'answer': 'Yes, you can permanently delete your account by going to "Account Settings" and selecting "Delete Account". Please note that this action is irreversible and will remove all your data, order history, and preferences.',
                'order': 5
            },
            {
                'question': 'How do I enable two-factor authentication?',
                'answer': 'Go to "Security Settings" in your account dashboard. Enable two-factor authentication and follow the setup instructions. You can use an authenticator app or SMS verification for added security.',
                'order': 6
            }
        ]
        
        for faq_data in account_faqs:
            FAQ.objects.create(category=account_category, **faq_data)

        # Orders & Shipping
        orders_category = FAQCategory.objects.create(
            name="Orders & Shipping",
            description="Questions about placing orders, order status, shipping, and delivery",
            order=2
        )
        
        orders_faqs = [
            {
                'question': 'How do I track my order?',
                'answer': 'After placing an order, you\'ll receive an email with tracking information. You can also log into your account and visit "My Orders" to see real-time tracking updates and delivery status.',
                'order': 1
            },
            {
                'question': 'How long does shipping take?',
                'answer': 'Standard shipping takes 3-5 business days, express shipping takes 1-2 business days, and overnight shipping delivers the next business day. Processing time is typically 1-2 business days before shipping.',
                'order': 2
            },
            {
                'question': 'Can I change or cancel my order?',
                'answer': 'Orders can be modified or cancelled within 2 hours of placement. After this time, orders enter processing and cannot be changed. Contact customer support immediately if you need to make changes.',
                'order': 3
            },
            {
                'question': 'What are your shipping costs?',
                'answer': 'Shipping costs vary by location and delivery speed: Standard shipping $5.99, Express $12.99, Overnight $24.99. Free standard shipping is available on orders over $50.',
                'order': 4
            },
            {
                'question': 'Do you ship internationally?',
                'answer': 'Yes, we ship to most countries worldwide. International shipping takes 7-14 business days and costs vary by destination. Customs fees and import duties may apply and are the customer\'s responsibility.',
                'order': 5
            },
            {
                'question': 'My package is lost or damaged. What should I do?',
                'answer': 'Contact us immediately with your order number and photos of any damage. We\'ll work with the shipping carrier to locate lost packages or file damage claims. We\'ll replace or refund damaged items promptly.',
                'order': 6
            }
        ]
        
        for faq_data in orders_faqs:
            FAQ.objects.create(category=orders_category, **faq_data)

        # Returns & Refunds
        returns_category = FAQCategory.objects.create(
            name="Returns & Refunds",
            description="Information about return policies, refund processes, and exchanges",
            order=3
        )
        
        returns_faqs = [
            {
                'question': 'What is your return policy?',
                'answer': 'We accept returns within 30 days of delivery for most items. Products must be in original condition with tags attached. Digital products, personalized items, and perishables cannot be returned.',
                'order': 1
            },
            {
                'question': 'How do I return an item?',
                'answer': 'Log into your account, go to "My Orders", and select "Return Items" next to your order. Choose items to return, select a reason, and print the prepaid return label. Package items securely and drop off at any authorized location.',
                'order': 2
            },
            {
                'question': 'When will I receive my refund?',
                'answer': 'Refunds are processed within 3-5 business days after we receive and inspect your returned items. The refund will appear on your original payment method within 5-10 business days depending on your bank or card issuer.',
                'order': 3
            },
            {
                'question': 'Can I exchange an item instead of returning it?',
                'answer': 'Yes, you can exchange items for different sizes or colors if available. Select "Exchange" instead of "Return" when initiating the return process. We\'ll send the new item once we receive your return.',
                'order': 4
            },
            {
                'question': 'Who pays for return shipping?',
                'answer': 'We provide free return shipping labels for defective items, wrong items sent, or our errors. For other returns (size, color, changed mind), return shipping costs $6.99 and will be deducted from your refund.',
                'order': 5
            },
            {
                'question': 'Can I return items bought with a discount or coupon?',
                'answer': 'Yes, but refunds will reflect the actual amount paid after discounts. If you used a coupon code, the discount amount cannot be refunded as cash or store credit.',
                'order': 6
            }
        ]
        
        for faq_data in returns_faqs:
            FAQ.objects.create(category=returns_category, **faq_data)

        # Payment & Billing
        payment_category = FAQCategory.objects.create(
            name="Payment & Billing",
            description="Questions about payment methods, billing, invoices, and charges",
            order=4
        )
        
        payment_faqs = [
            {
                'question': 'What payment methods do you accept?',
                'answer': 'We accept all major credit cards (Visa, MasterCard, American Express, Discover), PayPal, Apple Pay, Google Pay, and bank transfers. Gift cards and store credit can also be used for purchases.',
                'order': 1
            },
            {
                'question': 'Is it safe to use my credit card on your website?',
                'answer': 'Yes, our website uses 256-bit SSL encryption to protect your payment information. We\'re PCI DSS compliant and use secure payment processors. We never store your complete credit card details on our servers.',
                'order': 2
            },
            {
                'question': 'Why was my payment declined?',
                'answer': 'Common reasons for payment decline: insufficient funds, incorrect card details, expired card, or bank security measures. Contact your bank or try a different payment method. Ensure billing address matches your card\'s registered address.',
                'order': 3
            },
            {
                'question': 'Can I use multiple payment methods for one order?',
                'answer': 'Currently, we only accept one payment method per order. You can use gift cards or store credit in combination with another payment method to cover the remaining balance.',
                'order': 4
            },
            {
                'question': 'Where can I find my invoice or receipt?',
                'answer': 'Order confirmations and invoices are emailed automatically after purchase. You can also access them anytime by logging into your account and visiting "My Orders" section.',
                'order': 5
            },
            {
                'question': 'I see an unexpected charge on my card. What should I do?',
                'answer': 'Check your email for order confirmations first. Log into your account to review recent orders. If you don\'t recognize a charge, contact us immediately with the transaction details and we\'ll investigate.',
                'order': 6
            }
        ]
        
        for faq_data in payment_faqs:
            FAQ.objects.create(category=payment_category, **faq_data)

        # Technical Support
        technical_category = FAQCategory.objects.create(
            name="Technical Support",
            description="Help with website issues, mobile app problems, and technical difficulties",
            order=5
        )
        
        technical_faqs = [
            {
                'question': 'The website is not loading properly. What should I do?',
                'answer': 'Try refreshing the page, clearing your browser cache and cookies, or using a different browser. Check your internet connection and disable browser extensions temporarily. If problems persist, try accessing from a different device.',
                'order': 1
            },
            {
                'question': 'Why can\'t I add items to my cart?',
                'answer': 'This could be due to browser cookies being disabled, JavaScript being turned off, or browser compatibility issues. Try enabling cookies, updating your browser, or clearing your cache. Contact support if the issue continues.',
                'order': 2
            },
            {
                'question': 'The mobile app keeps crashing. How can I fix this?',
                'answer': 'Try force-closing and reopening the app, restarting your device, or updating to the latest app version. Clear the app cache in your device settings. If crashes continue, uninstall and reinstall the app.',
                'order': 3
            },
            {
                'question': 'I\'m not receiving email notifications from you.',
                'answer': 'Check your spam/junk folder first. Add our email address to your contacts or safe sender list. Verify your email address in account settings is correct. Some email providers may block promotional emails.',
                'order': 4
            },
            {
                'question': 'How do I update the mobile app?',
                'answer': 'Go to your device\'s app store (App Store for iOS, Google Play for Android), search for our app, and tap "Update" if available. Enable automatic updates in your app store settings to receive updates automatically.',
                'order': 5
            },
            {
                'question': 'The search function isn\'t working correctly.',
                'answer': 'Try using different search terms, check spelling, or use more general keywords. Clear your browser cache or try searching from a different page. Our search suggestions can help you find what you\'re looking for.',
                'order': 6
            }
        ]
        
        for faq_data in technical_faqs:
            FAQ.objects.create(category=technical_category, **faq_data)

        # General Support
        general_category = FAQCategory.objects.create(
            name="General Support",
            description="General questions about our service, policies, and contact information",
            order=6
        )
        
        general_faqs = [
            {
                'question': 'How can I contact customer support?',
                'answer': 'You can reach us through: live chat on our website, email at support@example.com, phone at 1-800-123-4567 (Mon-Fri 9AM-6PM), or by creating a support ticket in your account dashboard.',
                'order': 1
            },
            {
                'question': 'What are your business hours?',
                'answer': 'Our customer support is available Monday through Friday, 9:00 AM to 6:00 PM EST. Live chat and email support are available 24/7. We respond to emails within 24 hours on business days.',
                'order': 2
            },
            {
                'question': 'Do you have a mobile app?',
                'answer': 'Yes, our mobile app is available for both iOS and Android devices. Download it from the App Store or Google Play Store. The app offers all website features plus exclusive mobile-only deals and notifications.',
                'order': 3
            },
            {
                'question': 'How do I subscribe to your newsletter?',
                'answer': 'Enter your email address in the newsletter signup box on our homepage footer. You can also subscribe during checkout or in your account settings. Subscribers receive exclusive offers, new product announcements, and helpful tips.',
                'order': 4
            },
            {
                'question': 'Can I request a feature or suggest improvements?',
                'answer': 'Absolutely! We value customer feedback. Send your suggestions through our contact form, email, or support chat. While we can\'t implement every suggestion, we carefully review all feedback for future improvements.',
                'order': 5
            },
            {
                'question': 'How do I unsubscribe from marketing emails?',
                'answer': 'Click the "Unsubscribe" link at the bottom of any marketing email, or log into your account and update your email preferences in settings. You\'ll continue to receive important account and order-related emails.',
                'order': 6
            },
            {
                'question': 'Do you offer bulk or corporate discounts?',
                'answer': 'Yes, we offer special pricing for bulk orders and corporate accounts. Contact our sales team at sales@example.com with your requirements. Discounts typically apply to orders of 50+ units or annual contracts.',
                'order': 7
            },
            {
                'question': 'What is your privacy policy?',
                'answer': 'Our privacy policy outlines how we collect, use, and protect your personal information. You can read the full policy on our website footer. We never sell your data to third parties and use industry-standard security measures.',
                'order': 8
            }
        ]
        
        for faq_data in general_faqs:
            FAQ.objects.create(category=general_category, **faq_data)

        self.stdout.write('Created FAQ categories and questions:')
        for category in FAQCategory.objects.all():
            count = category.faqs.count()
            self.stdout.write(f'  - {category.name}: {count} questions')