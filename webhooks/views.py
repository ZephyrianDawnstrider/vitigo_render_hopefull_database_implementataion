# webhooks/views.py

# Python standard library
import json
import logging

# Django imports
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

# Local application imports
from query_management.models import Query
from .models import WhatsAppWebhook, FacebookMessengerWebhook, InstagramWebhook
from .utils import (
    
    #
    get_or_create_user_whatsapp,
    get_latest_state,
    get_queries_whatsapp,
    send_whatsapp_response,
    
    # 
    get_or_create_user_messenger,
    get_messenger_latest_state,
    get_queries_messenger,
    send_messenger_response,
    send_messenger_media,

    #
    get_or_create_user_instagram,
    get_instagram_latest_state,
    get_queries_instagram,
    send_instagram_response,
    send_instagram_media,
    verify_instagram_signature,
    subscribe_to_webhooks,
    
    format_query_status,

    # Constants
    MENU_TEXT,
    MESSENGER_MENU_TEXT,
    INSTAGRAM_MENU_TEXT
)

# Logger configuration
logger = logging.getLogger('query_management')

# webhooks/views.py
@csrf_exempt 
def whatsapp_webhook(request):
    if request.method == 'GET':
        logger.info("Received WhatsApp verification request")
        # Verification logic remains same
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if mode and token and mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp webhook verified successfully")
            return HttpResponse(challenge, content_type='text/plain')
        logger.warning(f"Invalid verification attempt with token: {token}")
        return HttpResponse('Invalid verification token', status=403)

    if request.method == 'POST':
        logger.info("Received WhatsApp webhook POST request")
        try:
            data = json.loads(request.body)
            logger.debug(f"Webhook payload: {data}")
            
            if 'object' not in data or data['object'] != 'whatsapp_business_account':
                logger.warning("Invalid webhook object type")
                return HttpResponse('Invalid webhook object', status=400)
            
            if 'entry' not in data or not data['entry']:
                logger.warning("Missing entry data")
                return HttpResponse('Missing entry data', status=400)
            
            entry = data['entry'][0]
            if 'changes' not in entry:
                logger.warning("Missing changes array")
                return HttpResponse('Missing changes data', status=400)
            
            changes = entry['changes'][0]
            if 'value' not in changes:
                logger.warning("Missing value object")
                return HttpResponse('Missing value data', status=400)
            
            value = changes['value']
            
            # Handle different types of webhooks
            if 'messages' in value and value['messages']:
                message = value['messages'][0]
                # Continue with existing message handling code
                message_id = message['id']
                
                # Check if message already processed
                if WhatsAppWebhook.objects.filter(message_id=message_id).exists():
                    logger.warning(f"Duplicate message received: {message_id}")
                    return HttpResponse('OK', status=200)
                
                phone_number = message['from']
                message_text = message['text']['body'].strip()
                
                logger.info(f"Processing message from {phone_number}: {message_text[:50]}...")
                
                # Get or create user
                user = get_or_create_user_whatsapp(phone_number)
                logger.debug(f"User retrieved/created: {user.id}")
                
                # Get latest state
                last_webhook = get_latest_state(phone_number)
                current_state = last_webhook.conversation_state if last_webhook else 'MENU'
                logger.debug(f"Current conversation state: {current_state}")
                
                # Create webhook record with initialized temp_data
                webhook = WhatsAppWebhook.objects.create(
                    message_id=message['id'],
                    from_number=phone_number,
                    message_body=message_text,
                    timestamp=timezone.now(),
                    status='RECEIVED',
                    user=user,
                    conversation_state=current_state,
                    temp_data={}  # Initialize empty dict
                )
                logger.info(f"Created webhook record: {webhook.id}")

                # Handle conversation states
                if message_text == '3':  # Exit
                    logger.info(f"User {phone_number} exiting conversation")
                    send_whatsapp_response(phone_number, "Thank you for using VitiGo Query Management. Goodbye!")
                    webhook.conversation_state = 'MENU'
                    webhook.save()
                    return HttpResponse('OK', status=200)

                if current_state == 'MENU' or message_text == '0':
                    logger.debug(f"Processing menu option: {message_text}")
                    if message_text == '1':
                        webhook.conversation_state = 'AWAITING_SUBJECT'
                        webhook.save()
                        send_whatsapp_response(phone_number, "Please enter the subject for your query:")
                    
                    elif message_text == '2':
                        queries = get_queries_whatsapp(phone_number)
                        if queries:
                            response = "Your recent queries:\n\n"
                            response += "\n".join(format_query_status(q) for q in queries)
                            response += "\n\nReply 0 for main menu, 3 to exit"
                        else:
                            response = "You have no queries yet.\n\nReply 0 for main menu, 3 to exit"
                        send_whatsapp_response(phone_number, response)
                    
                    else:
                        send_whatsapp_response(phone_number, MENU_TEXT)

                elif current_state == 'AWAITING_SUBJECT':
                    logger.debug(f"Processing subject input: {message_text[:50]}...")
                    webhook.temp_data = {'subject': message_text}  # Create new dict
                    webhook.conversation_state = 'AWAITING_DESCRIPTION'
                    webhook.save()
                    send_whatsapp_response(phone_number, "Please provide details for your query:")

                elif current_state == 'AWAITING_DESCRIPTION':
                    logger.debug(f"Processing query description: {message_text[:50]}...")
                    # Get last webhook with subject
                    last_webhook = WhatsAppWebhook.objects.filter(
                        from_number=phone_number,
                        conversation_state='AWAITING_DESCRIPTION'
                    ).exclude(id=webhook.id).last()
                    
                    if not last_webhook or 'subject' not in last_webhook.temp_data:
                        logger.error("Subject not found in conversation flow")
                        send_whatsapp_response(phone_number, "Sorry, there was an error. Please start over.\n\n" + MENU_TEXT)
                        webhook.conversation_state = 'MENU'
                        webhook.save()
                        return HttpResponse('OK', status=200)

                    # Create new query
                    query = Query.objects.create(
                        user=user,
                        subject=last_webhook.temp_data['subject'],
                        description=message_text,
                        source='WHATSAPP',
                        status='NEW',
                        contact_phone=phone_number
                    )
                    logger.info(f"Created new query: {query.query_id}")
                    
                    webhook.conversation_state = 'MENU'
                    webhook.save()
                    
                    response = """
Your query has been submitted successfully! 
Our team will review it and get back to you.

Reply 0 for main menu, 3 to exit
"""
                    send_whatsapp_response(phone_number, response)
            
            elif 'statuses' in value:
                # Handle message status updates
                logger.info("Received status update webhook")
                return HttpResponse('OK', status=200)
                
            else:
                # Handle other webhook types or system messages
                logger.info(f"Received webhook type with fields: {list(value.keys())}")
                return HttpResponse('OK', status=200)

            return HttpResponse('OK', status=200)
            
        except KeyError as e:
            logger.error(f"Invalid webhook payload structure: {str(e)}", exc_info=True)
            return HttpResponse('Invalid webhook payload', status=400)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {str(e)}", exc_info=True)
            return HttpResponse('Invalid JSON payload', status=400)
        except Exception as e:
            logger.error(f"Unexpected error processing webhook: {str(e)}", exc_info=True)
            return HttpResponse('Error processing webhook', status=500)

@csrf_exempt
def messenger_webhook(request):
    if request.method == 'GET':
        logger.info("Received Messenger verification request")
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if mode and token and mode == 'subscribe' and token == settings.FACEBOOK_VERIFY_TOKEN:
            logger.info("Messenger webhook verified successfully")
            return HttpResponse(challenge, content_type='text/plain')
        logger.warning(f"Invalid Messenger verification attempt with token: {token}")
        return HttpResponse('Invalid verification token', status=403)

    if request.method == 'POST':
        logger.info("Received Messenger webhook POST request")
        try:
            data = json.loads(request.body)
            logger.debug(f"Messenger webhook payload: {data}")
            
            for entry in data['entry']:
                for messaging_event in entry['messaging']:
                    sender_psid = messaging_event['sender']['id']
                    
                    if 'message' in messaging_event:
                        message_text = messaging_event['message'].get('text', '')
                        message_id = messaging_event['message']['mid']
                        
                        # Check for duplicate message
                        if FacebookMessengerWebhook.objects.filter(message_id=message_id).exists():
                            logger.warning(f"Duplicate Messenger message received: {message_id}")
                            continue
                        
                        # Get or create user
                        user = get_or_create_user_messenger(sender_psid)
                        
                        # Get latest state
                        last_webhook = get_messenger_latest_state(sender_psid)
                        current_state = last_webhook.conversation_state if last_webhook else 'MENU'
                        
                        # Create webhook record
                        webhook = FacebookMessengerWebhook.objects.create(
                            psid=sender_psid,
                            message_id=message_id,
                            message_body=message_text,
                            timestamp=timezone.now(),
                            status='RECEIVED',
                            user=user,
                            conversation_state=current_state
                        )

                        # Handle conversation states
                        if message_text == '3':  # Exit
                            send_messenger_response(sender_psid, "Thank you for using VitiGo Query Management. Goodbye!")
                            webhook.conversation_state = 'MENU'
                            webhook.save()
                            continue

                        if current_state == 'MENU' or message_text == '0':
                            if message_text == '1':
                                webhook.conversation_state = 'AWAITING_SUBJECT'
                                webhook.save()
                                send_messenger_response(sender_psid, "Please enter the subject for your query:")
                            
                            elif message_text == '2':
                                queries = get_queries_messenger(sender_psid)
                                if queries:
                                    response = "Your recent queries:\n\n"
                                    response += "\n".join(format_query_status(q) for q in queries)
                                    response += "\n\nType 0 for main menu, 3 to exit"
                                else:
                                    response = "You have no queries yet.\n\nType 0 for main menu, 3 to exit"
                                send_messenger_response(sender_psid, response)
                            
                            else:
                                send_messenger_response(sender_psid, MESSENGER_MENU_TEXT)

                        elif current_state == 'AWAITING_SUBJECT':
                            webhook.temp_data = {'subject': message_text}
                            webhook.conversation_state = 'AWAITING_DESCRIPTION'
                            webhook.save()
                            send_messenger_response(sender_psid, "Please provide details for your query:")

                        elif current_state == 'AWAITING_DESCRIPTION':
                            last_webhook = FacebookMessengerWebhook.objects.filter(
                                psid=sender_psid,
                                conversation_state='AWAITING_DESCRIPTION'
                            ).exclude(id=webhook.id).last()

                            if not last_webhook or 'subject' not in last_webhook.temp_data:
                                send_messenger_response(sender_psid, "Sorry, there was an error. Please start over.\n\n" + MESSENGER_MENU_TEXT)
                                webhook.conversation_state = 'MENU'
                                webhook.save()
                                continue

                            # Create new query
                            query = Query.objects.create(
                                user=user,
                                subject=last_webhook.temp_data['subject'],
                                description=message_text,
                                source='MESSENGER',
                                status='NEW'
                            )
                            
                            webhook.conversation_state = 'MENU'
                            webhook.save()
                            
                            response = """
Your query has been submitted successfully! 
Our team will review it and get back to you.

Type 0 for main menu, 3 to exit
"""
                            send_messenger_response(sender_psid, response)
            
            return HttpResponse('OK', status=200)
            
        except Exception as e:
            logger.error(f"Error processing Messenger webhook: {str(e)}", exc_info=True)
            return HttpResponse('Error processing webhook', status=500)
        

@csrf_exempt
def instagram_webhook(request):
    logger.info("====== Instagram Webhook Request Started ======")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request Path: {request.path}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    
    if request.method == 'GET':
        logger.info("Processing GET request (webhook verification)")
        logger.info(f"Query Parameters: {dict(request.GET)}")
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        logger.info(f"Verification Parameters - Mode: {mode}, Token: {token}, Challenge: {challenge}")
        
        if mode and token and mode == 'subscribe' and token == settings.INSTAGRAM_VERIFY_TOKEN:
            logger.info("Instagram webhook verified successfully")
            logger.info(f"Responding with challenge: {challenge}")
            return HttpResponse(challenge, content_type='text/plain')
            
        logger.warning(f"Invalid Instagram verification attempt with token: {token}")
        logger.warning(f"Expected token: {settings.INSTAGRAM_VERIFY_TOKEN}")
        return HttpResponse('Invalid verification token', status=403)

    if request.method == 'POST':
        logger.info("Processing POST request (webhook event)")
        logger.info(f"Raw Request Body: {request.body.decode()}")
        
        signature = request.headers.get('X-Hub-Signature-256', '')
        logger.info(f"Webhook Signature: {signature}")
        
        if not verify_instagram_signature(
            signature, 
            request.body, 
            settings.INSTAGRAM_APP_SECRET
        ):
            logger.warning("Invalid Instagram webhook signature")
            logger.warning(f"Request signature: {signature}")
            logger.warning(f"App Secret used: {settings.INSTAGRAM_APP_SECRET[:5]}...")
            return HttpResponse('Invalid signature', status=403)
            
        try:
            data = json.loads(request.body)
            logger.info(f"Parsed webhook payload: {json.dumps(data, indent=2)}")
            
            if 'entry' not in data:
                logger.warning("No 'entry' field in webhook payload")
                return HttpResponse('Missing entry field', status=400)
                
            logger.info(f"Number of entries: {len(data['entry'])}")
            
            for entry in data['entry']:
                logger.info(f"Processing entry: {json.dumps(entry, indent=2)}")
                
                # Handle real-time messages (from actual users)
                if 'changes' in entry:
                    for change in entry['changes']:
                        if change['field'] == 'messages':
                            value = change.get('value', {})
                            sender_igsid = value.get('sender', {}).get('id')
                            message_data = value.get('message', {})
                            
                            if not sender_igsid or not message_data:
                                logger.warning("Missing sender ID or message data in changes")
                                continue
                                
                            message_id = message_data.get('mid')
                            message_text = message_data.get('text', '')
                            
                            logger.info(f"Processing real-time message - IGSID: {sender_igsid}, Message ID: {message_id}, Text: {message_text}")
                            
                            process_instagram_message(
                                sender_igsid=sender_igsid,
                                message_id=message_id,
                                message_text=message_text,
                                attachments=message_data.get('attachments', [])
                            )
                
                # Handle test messages (from Meta testing)
                if 'messaging' in entry:
                    for messaging in entry.get('messaging', []):
                        logger.info(f"Processing test messaging object: {json.dumps(messaging, indent=2)}")
                        
                        if 'sender' not in messaging:
                            logger.warning("No sender information in messaging object")
                            continue
                            
                        sender_igsid = messaging['sender']['id']
                        message = messaging.get('message', {})
                        message_id = message.get('mid')
                        
                        if not message_id:
                            logger.warning("No message ID found in messaging object")
                            continue
                            
                        logger.info(f"Processing test message - IGSID: {sender_igsid}, Message ID: {message_id}")
                        
                        process_instagram_message(
                            sender_igsid=sender_igsid,
                            message_id=message_id,
                            message_text=message.get('text', ''),
                            attachments=message.get('attachments', [])
                        )
            
            logger.info("Webhook processing completed successfully")
            return HttpResponse('OK', status=200)
            
        except Exception as e:
            logger.error(f"Error processing Instagram webhook: {str(e)}", exc_info=True)
            return HttpResponse('Error processing webhook', status=500)
        
    logger.info("====== Instagram Webhook Request Ended ======")

def process_instagram_message(sender_igsid, message_id, message_text, attachments=None):
    """Process incoming Instagram messages"""
    logger.info(f"Processing message - IGSID: {sender_igsid}, Message ID: {message_id}, Text: {message_text}")
    
    if not message_id:
        logger.warning("No message ID provided")
        return
        
    # Check for duplicate message
    if InstagramWebhook.objects.filter(message_id=message_id).exists():
        logger.warning(f"Duplicate Instagram message received: {message_id}")
        return
    
    # Get or create user
    try:
        user = get_or_create_user_instagram(sender_igsid)
        logger.info(f"User retrieved/created: {user.id}")
    except Exception as e:
        logger.error(f"Error getting/creating user: {str(e)}", exc_info=True)
        return
    
    # Get latest state
    try:
        last_webhook = get_instagram_latest_state(sender_igsid)
        current_state = last_webhook.conversation_state if last_webhook else 'MENU'
        logger.info(f"Current conversation state: {current_state}")
    except Exception as e:
        logger.error(f"Error getting conversation state: {str(e)}", exc_info=True)
        current_state = 'MENU'
    
    message_type = 'text'
    media_url = None
    
    # Handle attachments if present
    if attachments:
        logger.info("Processing message attachments")
        for attachment in attachments:
            logger.info(f"Processing attachment: {attachment}")
            if attachment['type'] in ['image', 'video', 'audio']:
                message_type = attachment['type']
                media_url = attachment.get('payload', {}).get('url')
                logger.info(f"Media attachment found - Type: {message_type}, URL: {media_url}")
    
    # Create webhook record
    try:
        webhook = InstagramWebhook.objects.create(
            igsid=sender_igsid,
            message_id=message_id,
            message_body=message_text,
            message_type=message_type,
            media_url=media_url,
            timestamp=timezone.now(),
            status='RECEIVED',
            user=user,
            conversation_state=current_state
        )
        logger.info(f"Webhook record created: {webhook.id}")
    except Exception as e:
        logger.error(f"Error creating webhook record: {str(e)}", exc_info=True)
        return

    # Handle conversation states
    try:
        if message_text == '3':  # Exit
            logger.info("User requested exit")
            send_instagram_response(sender_igsid, "Thank you for using VitiGo Query Management. Goodbye!")
            webhook.conversation_state = 'MENU'
            webhook.save()
            logger.info("Exit response sent successfully")
            return

        if current_state == 'MENU' or message_text == '0':
            logger.info("Processing MENU state")
            if message_text == '1':
                webhook.conversation_state = 'AWAITING_SUBJECT'
                webhook.save()
                send_instagram_response(sender_igsid, "Please enter the subject for your query:")
                logger.info("Subject prompt sent successfully")
            
            elif message_text == '2':
                queries = get_queries_instagram(sender_igsid)
                logger.info(f"Retrieved {len(queries)} queries for user")
                if queries:
                    response = "Your recent queries:\n\n"
                    response += "\n".join(format_query_status(q) for q in queries)
                    response += "\n\nType 0 for main menu, 3 to exit"
                else:
                    response = "You have no queries yet.\n\nType 0 for main menu, 3 to exit"
                send_instagram_response(sender_igsid, response)
                logger.info("Queries response sent successfully")
            
            else:
                send_instagram_response(sender_igsid, INSTAGRAM_MENU_TEXT)
                logger.info("Menu text sent successfully")

        elif current_state == 'AWAITING_SUBJECT':
            logger.info("Processing AWAITING_SUBJECT state")
            webhook.temp_data = {'subject': message_text}
            webhook.conversation_state = 'AWAITING_DESCRIPTION'
            webhook.save()
            send_instagram_response(sender_igsid, "Please provide details for your query:")
            logger.info("Description prompt sent successfully")

        elif current_state == 'AWAITING_DESCRIPTION':
            logger.info("Processing AWAITING_DESCRIPTION state")
            last_webhook = InstagramWebhook.objects.filter(
                igsid=sender_igsid,
                conversation_state='AWAITING_DESCRIPTION'
            ).exclude(id=webhook.id).last()
            
            logger.info(f"Previous webhook found: {last_webhook.id if last_webhook else None}")

            if not last_webhook or 'subject' not in last_webhook.temp_data:
                logger.warning("Missing subject in previous webhook")
                send_instagram_response(sender_igsid, "Sorry, there was an error. Please start over.\n\n" + INSTAGRAM_MENU_TEXT)
                webhook.conversation_state = 'MENU'
                webhook.save()
                return

            # Create new query
            query = Query.objects.create(
                user=user,
                subject=last_webhook.temp_data['subject'],
                description=message_text,
                source='INSTAGRAM',
                status='NEW'
            )
            logger.info(f"New query created: {query.id}")
            
            webhook.conversation_state = 'MENU'
            webhook.save()
            
            response = """
Your query has been submitted successfully! 
Our team will review it and get back to you.

Type 0 for main menu, 3 to exit
"""
            send_instagram_response(sender_igsid, response)
            logger.info("Query confirmation sent successfully")
            
    except Exception as e:
        logger.error(f"Error processing message state: {str(e)}", exc_info=True)
        try:
            send_instagram_response(sender_igsid, "Sorry, there was an error. Please try again.\n\n" + INSTAGRAM_MENU_TEXT)
            webhook.conversation_state = 'MENU'
            webhook.save()
        except Exception as inner_e:
            logger.error(f"Error sending error response: {str(inner_e)}", exc_info=True)

GREETING_PATTERNS = [
    'hi', 'hello', 'hey', 'hii', 'hola', 'greetings', 
    'good morning', 'good afternoon', 'good evening',
    'hi there', 'hello there', 'namaste'
]

@csrf_exempt
def chatbot_webhook(request):
    """Handle Crisp chatbot webhooks"""
    logger.info("====== Crisp Chatbot Webhook Request Started ======")
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Received chatbot webhook data: {json.dumps(data, indent=2)}")
            
            message_data = data.get('data', {})
            message_content = message_data.get('content', '').strip()
            user_data = message_data.get('user', {})
            nickname = user_data.get('nickname', '')
            
            # Skip processing for greeting messages
            if is_greeting(message_content):
                logger.info(f"Skipping greeting message: {message_content}")
                return JsonResponse({'status': 'success', 'message': 'Greeting message ignored'})
            
            # Get or create user
            try:
                User = get_user_model()
                email = f"{nickname}@temp.com"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'is_active': True,
                    }
                )
                if created:
                    logger.info(f"Created new user with email: {email}")
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'User creation failed'}, status=500)
            
            # Create query
            try:
                query = Query.objects.create(
                    user=user,
                    subject=f"Chat Query from {nickname}",
                    description=message_content,
                    source='CHATBOT',
                    status='NEW',
                    query_type='GENERAL'
                )
                logger.info(f"Created new query {query.query_id} for user {nickname}")
            except Exception as e:
                logger.error(f"Error creating query: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'Query creation failed'}, status=500)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Query created successfully',
                'query_id': query.query_id
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def is_greeting(message):
    """Check if message is a greeting"""
    message = message.lower().strip()
    return (
        message in GREETING_PATTERNS or
        len(message) < 10 
    )