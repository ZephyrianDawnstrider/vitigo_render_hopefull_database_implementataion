# webhooks/utils.py
import re
from django.contrib.auth import get_user_model
from query_management.models import Query
from .models import WhatsAppWebhook, FacebookMessengerWebhook, InstagramWebhook
from django.conf import settings
import requests
import logging
import hmac
import hashlib

logger = logging.getLogger('query_management')

MENU_TEXT = """
Welcome to VitiGo Query Management!
1. Create new query
2. View my queries
3. Exit

Reply with a number to continue.
"""

MESSENGER_MENU_TEXT = """
Welcome to VitiGo Query Management!
1. Create new query
2. View my queries
3. Exit

Type a number to continue.
"""

INSTAGRAM_MENU_TEXT = """
Welcome to VitiGo Query Management!
1. Create new query
2. View my queries
3. Exit

Type a number to continue.
"""

def get_or_create_user_whatsapp(phone_number):
    """Get or create user based on phone number"""
    logger.debug(f"Getting/creating user for phone: {phone_number}")
    User = get_user_model()
    user = User.objects.filter(phone_number=phone_number).first()
    if not user:
        logger.info(f"Creating new user for phone: {phone_number}")
        email = f"{phone_number}@temp.com"
        user = User.objects.create(
            email=email,
            phone_number=phone_number,
            is_active=True
        )
    return user

def get_or_create_user_messenger(psid):
    """Get or create user based on psid"""
    logger.debug(f"Getting/creating user for psid: {psid}")
    User = get_user_model()
    user = User.objects.filter(psid=psid).first()
    if not user:
        logger.info(f"Creating new user for psid: {psid}")
        email = f"{psid}@temp.com"
        user = User.objects.create(
            email=email,
            psid=psid,
            is_active=True
        )
    return user

def get_or_create_user_instagram(igsid):
    """Get or create user based on Instagram-scoped ID"""
    logger.debug(f"Getting/creating user for IGSID: {igsid}")
    User = get_user_model()
    user = User.objects.filter(igsid=igsid).first()
    if not user:
        logger.info(f"Creating new user for IGSID: {igsid}")
        email = f"{igsid}@temp.instagram.com"
        user = User.objects.create(
            email=email,
            igsid=igsid,
            is_active=True
        )
    return user

def get_latest_state(phone_number):
    """Get user's latest conversation state"""
    logger.debug(f"Fetching latest state for phone: {phone_number}")
    return WhatsAppWebhook.objects.filter(
        from_number=phone_number
    ).order_by('-created_at').first()

def get_messenger_latest_state(psid):
    """Get user's latest messenger conversation state"""
    logger.debug(f"Fetching latest messenger state for PSID: {psid}")
    return FacebookMessengerWebhook.objects.filter(
        psid=psid
    ).order_by('-created_at').first()

def get_instagram_latest_state(igsid):
    """Get user's latest Instagram conversation state"""
    logger.debug(f"Fetching latest Instagram state for IGSID: {igsid}")
    return InstagramWebhook.objects.filter(
        igsid=igsid
    ).order_by('-created_at').first()

def get_queries_whatsapp(phone_number):
    """Get queries for a phone number"""
    logger.debug(f"Fetching queries for phone: {phone_number}")
    return Query.objects.filter(
        contact_phone=phone_number
    ).order_by('-created_at')[:5]

def get_queries_messenger(psid):
    """Get queries for a PSID"""
    user = get_user_model().objects.filter(psid=psid).first()
    if not user:
        return []
    return Query.objects.filter(user=user).order_by('-created_at')[:5]

def get_queries_instagram(igsid):
    """Get queries for an Instagram user"""
    user = get_user_model().objects.filter(igsid=igsid).first()
    if not user:
        return []
    return Query.objects.filter(user=user).order_by('-created_at')[:5]

def verify_instagram_signature(request_signature, payload, app_secret):
    """Verify Instagram webhook payload signature"""
    expected_signature = hmac.new(
        app_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(request_signature, f"sha256={expected_signature}")


def subscribe_to_webhooks():
    url = f"https://graph.instagram.com/v21.0/{settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}/subscribed_apps"
    params = {
        "subscribed_fields": "messages,messaging_postbacks,messaging_optins,message_reactions,messaging_referral,messaging_seen",  
        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
    }
    response = requests.post(url, params=params)
    return response.json()


def format_query_status(query):
    """Format query status for WhatsApp message"""
    return f"""
Query #{query.query_id}
Subject: {query.subject}
Status: {query.get_status_display()}
Created: {query.created_at.strftime('%Y-%m-%d %H:%M')}
"""

def send_whatsapp_response(to_number, message):
    """Send WhatsApp message"""
    logger.info(f"Sending WhatsApp message to {to_number}")
    logger.debug(f"Message content: {message[:100]}...")
    
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    try:
        response = requests.post(url, json={
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }, headers={
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })
        
        response_data = response.json()
        if response.status_code != 200:
            logger.error(f"WhatsApp API error: {response_data}")
        else:
            logger.debug(f"WhatsApp API response: {response_data}")
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error(f"WhatsApp API request failed: {str(e)}", exc_info=True)
        raise

def send_messenger_response(psid, message_text):
    """Send Facebook Messenger message"""
    logger.info(f"Sending Messenger message to {psid}")
    logger.debug(f"Message content: {message_text[:100]}...")
    
    url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{settings.FACEBOOK_PAGE_ID}/messages"
    
    try:
        response = requests.post(url, json={
            "recipient": {"id": psid},
            "messaging_type": "RESPONSE",
            "message": {"text": message_text}
        }, headers={
            "Authorization": f"Bearer {settings.FACEBOOK_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })
        
        response_data = response.json()
        if response.status_code != 200:
            logger.error(f"Messenger API error: {response_data}")
        else:
            logger.debug(f"Messenger API response: {response_data}")
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Messenger API request failed: {str(e)}", exc_info=True)
        raise

def send_messenger_media(psid, media_url, media_type='image'):
    """Send media attachment via Messenger"""
    logger.info(f"Sending Messenger {media_type} to {psid}")
    
    url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{settings.FACEBOOK_PAGE_ID}/messages"
    
    try:
        response = requests.post(url, json={
            "recipient": {"id": psid},
            "message": {
                "attachment": {
                    "type": media_type,
                    "payload": {
                        "url": media_url,
                        "is_reusable": True
                    }
                }
            }
        }, headers={
            "Authorization": f"Bearer {settings.FACEBOOK_PAGE_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })
        
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Messenger media send failed: {str(e)}", exc_info=True)
        raise

def send_instagram_response(igsid, message_text):
    """Send Instagram DM"""
    logger.info(f"Sending Instagram message to {igsid}")
    
    url = f"https://graph.instagram.com/v21.0/{settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}/messages"
    
    payload = {
        "recipient": {"id": igsid},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    
    try:
        response = requests.post(url, 
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Instagram API error: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Instagram API request failed: {str(e)}", exc_info=True)
        raise

def send_instagram_media(igsid, media_url, media_type='image'):
    """Send media via Instagram DM"""
    logger.info(f"Sending Instagram {media_type} to {igsid}")
    
    url = f"https://graph.instagram.com/v21.0/{settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}/messages"
    
    try:
        response = requests.post(url, json={
            "recipient": {"id": igsid},
            "message": {
                "attachment": {
                    "type": media_type,
                    "payload": {
                        "url": media_url,
                    }
                }
            }
        }, headers={
            "Authorization": f"Bearer {settings.INSTAGRAM_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })
        
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Instagram media send failed: {str(e)}", exc_info=True)
        raise