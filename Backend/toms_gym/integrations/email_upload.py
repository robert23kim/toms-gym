"""
Email Upload Integration for Tom's Gym

This module processes emails forwarded from Google Chat to upload videos.
Users post in Chat with "t30g <weight> <lift_type>" and forward to the uploads email.

Usage:
    1. Set environment variables (see docs/google-chat-email-integration.md)
    2. Import and register the blueprint in app.py
    3. The background processor starts automatically or can be run separately
"""

import os
import re
import imaplib
import email
import smtplib
import tempfile
import logging
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from flask import Blueprint, jsonify, request
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint for API endpoints
email_upload_bp = Blueprint('email_upload', __name__)

# Configuration from environment
EMAIL_UPLOAD_ENABLED = os.environ.get('EMAIL_UPLOAD_ENABLED', 'false').lower() == 'true'
EMAIL_IMAP_SERVER = os.environ.get('EMAIL_IMAP_SERVER', 'imap.gmail.com')
EMAIL_IMAP_PORT = int(os.environ.get('EMAIL_IMAP_PORT', '993'))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_POLL_INTERVAL = int(os.environ.get('EMAIL_POLL_INTERVAL', '30'))
EMAIL_SMTP_SERVER = os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
EMAIL_SMTP_PORT = int(os.environ.get('EMAIL_SMTP_PORT', '587'))
EMAIL_SEND_CONFIRMATIONS = os.environ.get('EMAIL_SEND_CONFIRMATIONS', 'true').lower() == 'true'
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8080')

# Supported video MIME types
VIDEO_MIME_TYPES = {
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
    'video/x-matroska',
    'video/webm',
    'video/mpeg',
    'video/3gpp',
    'video/3gpp2',
}

# Lift type aliases
LIFT_TYPE_ALIASES = {
    'squat': 'Squat',
    'sq': 'Squat',
    'bench': 'Bench',
    'bp': 'Bench',
    'deadlift': 'Deadlift',
    'dl': 'Deadlift',
    'snatch': 'Snatch',
    'sn': 'Snatch',
    'clean': 'Clean',
    'c&j': 'Clean',
    'cj': 'Clean',
    'cleanandjerk': 'Clean',
    'overhead': 'Overhead',
    'ohp': 'Overhead',
    'press': 'Overhead',
}

# Statistics for monitoring
stats = {
    'emails_processed_today': 0,
    'errors_today': 0,
    'last_check': None,
    'last_error': None,
    'processor_running': False,
}


def parse_t30g_message(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a message for the t30g tag and extract metadata.
    
    Supports formats:
        - t30g 185kg Squat
        - t30g 315lbs Deadlift
        - t30g 100 (defaults to kg and Snatch)
        - Just hit a PR! t30g 200kg dl 💪
    
    Returns:
        Dict with weight_kg and lift_type, or None if no tag found
    """
    # Pattern: t30g followed by number, optional unit, optional lift type
    pattern = r't30g\s+(\d+(?:\.\d+)?)\s*(kg|kgs|lbs?|pounds?)?\s*(\w+)?'
    
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    
    weight = float(match.group(1))
    unit = (match.group(2) or 'kg').lower()
    lift_raw = match.group(3) or 'snatch'
    
    # Convert pounds to kg
    if unit.startswith('lb') or unit == 'pounds':
        weight = round(weight * 0.453592, 2)
    
    # Normalize lift type
    lift_type = LIFT_TYPE_ALIASES.get(lift_raw.lower(), 'Snatch')
    
    return {
        'weight_kg': weight,
        'lift_type': lift_type,
        'raw_text': text,
    }


def decode_email_header(header: str) -> str:
    """Decode an email header that may be encoded."""
    if not header:
        return ''
    
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    
    return ' '.join(decoded_parts)


def extract_email_address(from_header: str) -> str:
    """Extract just the email address from a From header."""
    # Handle formats like "John Smith <john@example.com>" or just "john@example.com"
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).lower()
    
    # Try to find an email pattern
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
    if match:
        return match.group(0).lower()
    
    return from_header.lower()


def get_email_body(msg: email.message.Message) -> str:
    """Extract the text body from an email message."""
    body = ''
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            
            # Skip attachments
            if 'attachment' in content_disposition:
                continue
            
            if content_type == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body += payload.decode(charset, errors='replace')
            elif content_type == 'text/html' and not body:
                # Fallback to HTML if no plain text
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    html = payload.decode(charset, errors='replace')
                    # Simple HTML to text conversion
                    body = re.sub(r'<[^>]+>', ' ', html)
                    body = re.sub(r'\s+', ' ', body)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
    
    return body


def extract_original_sender(body: str, forwarder_email: str) -> str:
    """
    Try to extract the original sender from a forwarded message.
    
    Forwarded messages typically contain headers like:
        ---------- Forwarded message ---------
        From: John Smith <john@example.com>
    """
    # Look for forwarded message patterns
    patterns = [
        r'From:\s*([^\n<]+<[^>]+>)',  # From: Name <email>
        r'From:\s*([\w\.-]+@[\w\.-]+\.\w+)',  # From: email@domain.com
    ]
    
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return extract_email_address(match.group(1))
    
    # Fallback to the forwarder
    return forwarder_email


def get_video_attachments(msg: email.message.Message) -> list:
    """Extract video attachments from an email message."""
    attachments = []
    
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition', ''))
        
        # Check if this is a video attachment
        if content_type in VIDEO_MIME_TYPES or content_type.startswith('video/'):
            filename = part.get_filename()
            if filename:
                filename = decode_email_header(filename)
            else:
                # Generate a filename based on content type
                ext = content_type.split('/')[-1]
                if ext == 'quicktime':
                    ext = 'mov'
                filename = f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{ext}'
            
            payload = part.get_payload(decode=True)
            if payload:
                attachments.append({
                    'filename': filename,
                    'content_type': content_type,
                    'data': payload,
                    'size': len(payload),
                })
    
    return attachments


def lookup_user_by_email(email_address: str) -> Optional[str]:
    """
    Look up a user ID by email address.
    
    Returns the user ID if found, None otherwise.
    """
    from toms_gym.db import get_db_connection
    import sqlalchemy
    
    session = get_db_connection()
    try:
        result = session.execute(
            sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'),
            {'email': email_address.lower()}
        ).fetchone()
        
        return str(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error looking up user: {e}")
        return None
    finally:
        session.close()


def get_active_competition() -> Optional[str]:
    """Get the ID of the currently active competition."""
    from toms_gym.db import get_db_connection
    import sqlalchemy
    
    session = get_db_connection()
    try:
        result = session.execute(
            sqlalchemy.text('''
                SELECT id FROM "Competition" 
                WHERE status = 'in_progress' 
                ORDER BY start_date DESC 
                LIMIT 1
            ''')
        ).fetchone()
        
        return str(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error getting active competition: {e}")
        return None
    finally:
        session.close()


def upload_video_to_backend(
    video_data: bytes,
    filename: str,
    content_type: str,
    user_id: str,
    competition_id: str,
    lift_type: str,
    weight_kg: float,
) -> Dict[str, Any]:
    """
    Upload a video to the Tom's Gym backend.
    
    Uses the existing /upload endpoint.
    """
    # Create a temporary file for the upload
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as f:
        f.write(video_data)
        temp_path = f.name
    
    try:
        with open(temp_path, 'rb') as video_file:
            files = {
                'video': (filename, video_file, content_type)
            }
            data = {
                'user_id': user_id,
                'competition_id': competition_id,
                'lift_type': lift_type,
                'weight': str(weight_kg),
            }
            
            response = requests.post(
                f"{BACKEND_URL}/upload",
                files=files,
                data=data,
                timeout=120,  # 2 minute timeout for large videos
            )
            
            response.raise_for_status()
            return response.json()
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def send_confirmation_email(
    to_email: str,
    success: bool,
    details: Dict[str, Any],
    error_message: Optional[str] = None,
):
    """Send a confirmation or error email to the user."""
    if not EMAIL_SEND_CONFIRMATIONS:
        return
    
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Cannot send confirmation: email credentials not configured")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USERNAME
        msg['To'] = to_email
        
        if success:
            msg['Subject'] = "✅ Tom's Gym - Video Uploaded Successfully"
            video_url = details.get('video_url', '')
            body = f"""
Your video has been uploaded to Tom's Gym!

Details:
- Weight: {details.get('weight_kg', 'N/A')} kg
- Lift Type: {details.get('lift_type', 'N/A')}
- Attempt ID: {details.get('attempt_id', 'N/A')}

🎬 Watch your video:
{video_url}

View your lift in the app: {os.environ.get('FRONTEND_URL', 'https://tomsgym.com')}

Thanks for sharing your lift! 💪
"""
        else:
            msg['Subject'] = "❌ Tom's Gym - Upload Failed"
            body = f"""
We couldn't process your video upload.

Error: {error_message or 'Unknown error'}

Please check:
1. Your message contains the "t30g" tag with weight (e.g., "t30g 185kg Squat")
2. A video file is attached
3. You're registered at Tom's Gym with this email address

If the problem persists, try forwarding the message again or contact support.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Confirmation email sent to {to_email}")
    
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")


def process_email(msg: email.message.Message, msg_id: str) -> Tuple[bool, str]:
    """
    Process a single email message.
    
    Returns:
        Tuple of (success, message)
    """
    # Get sender
    from_header = decode_email_header(msg.get('From', ''))
    forwarder_email = extract_email_address(from_header)
    
    logger.info(f"Processing email from {forwarder_email}")
    
    # Get email body
    body = get_email_body(msg)
    
    # Parse t30g tag
    metadata = parse_t30g_message(body)
    if not metadata:
        error = "No t30g tag found in message"
        logger.warning(error)
        send_confirmation_email(forwarder_email, False, {}, error)
        return False, error
    
    logger.info(f"Found t30g tag: {metadata['weight_kg']}kg {metadata['lift_type']}")
    
    # Get video attachments
    attachments = get_video_attachments(msg)
    if not attachments:
        error = "No video attachment found"
        logger.warning(error)
        send_confirmation_email(forwarder_email, False, metadata, error)
        return False, error
    
    # Use the first video attachment
    video = attachments[0]
    logger.info(f"Video attachment: {video['filename']} ({video['size'] / 1024 / 1024:.2f} MB)")
    
    # Try to find the original sender (for forwarded messages)
    user_email = extract_original_sender(body, forwarder_email)
    logger.info(f"User email: {user_email}")
    
    # Look up user
    user_id = lookup_user_by_email(user_email)
    if not user_id:
        # Fallback to forwarder
        user_id = lookup_user_by_email(forwarder_email)
    
    if not user_id:
        error = f"User not found for email {user_email}. Please register at Tom's Gym first."
        logger.warning(error)
        send_confirmation_email(forwarder_email, False, metadata, error)
        return False, error
    
    # Get active competition
    competition_id = get_active_competition()
    if not competition_id:
        error = "No active competition found"
        logger.warning(error)
        send_confirmation_email(forwarder_email, False, metadata, error)
        return False, error
    
    # Upload video
    try:
        result = upload_video_to_backend(
            video_data=video['data'],
            filename=video['filename'],
            content_type=video['content_type'],
            user_id=user_id,
            competition_id=competition_id,
            lift_type=metadata['lift_type'],
            weight_kg=metadata['weight_kg'],
        )
        
        logger.info(f"Upload successful: {result}")
        
        # Send confirmation with video URL
        send_confirmation_email(forwarder_email, True, {
            **metadata,
            'attempt_id': result.get('attempt_id'),
            'video_url': result.get('url'),
        })
        
        return True, f"Upload successful: {result.get('attempt_id')}"
    
    except Exception as e:
        error = f"Upload failed: {str(e)}"
        logger.error(error)
        send_confirmation_email(forwarder_email, False, metadata, error)
        return False, error


def check_inbox():
    """
    Check the email inbox for new messages and process them.
    
    Returns:
        Dict with processing results
    """
    global stats
    
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Email credentials not configured")
        return {'error': 'Email credentials not configured'}
    
    results = {
        'processed': 0,
        'succeeded': 0,
        'failed': 0,
        'errors': [],
    }
    
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(EMAIL_IMAP_SERVER, EMAIL_IMAP_PORT)
        mail.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        mail.select('INBOX')
        
        # Search for unread messages
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            logger.error(f"IMAP search failed: {status}")
            return {'error': 'IMAP search failed'}
        
        message_ids = messages[0].split()
        logger.info(f"Found {len(message_ids)} unread messages")
        
        for msg_id in message_ids:
            try:
                # Fetch the message
                status, data = mail.fetch(msg_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                msg = email.message_from_bytes(data[0][1])
                
                # Process the message
                success, message = process_email(msg, msg_id.decode())
                
                results['processed'] += 1
                if success:
                    results['succeeded'] += 1
                    stats['emails_processed_today'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(message)
                    stats['errors_today'] += 1
                
                # Mark as read (already done by FETCH, but ensure it)
                mail.store(msg_id, '+FLAGS', '\\Seen')
            
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")
                results['failed'] += 1
                results['errors'].append(str(e))
                stats['errors_today'] += 1
        
        mail.logout()
        
        stats['last_check'] = datetime.now().isoformat()
        return results
    
    except Exception as e:
        error_msg = f"Error checking inbox: {e}"
        logger.error(error_msg)
        stats['last_error'] = error_msg
        return {'error': error_msg}


def run_email_processor():
    """
    Run the email processor in a loop.
    
    This is meant to be run as a background thread or separate process.
    """
    global stats
    
    logger.info(f"Starting email processor (polling every {EMAIL_POLL_INTERVAL}s)")
    stats['processor_running'] = True
    
    while True:
        try:
            results = check_inbox()
            if results.get('processed', 0) > 0:
                logger.info(f"Processed {results['processed']} emails: "
                           f"{results['succeeded']} succeeded, {results['failed']} failed")
        except Exception as e:
            logger.error(f"Error in email processor loop: {e}")
            stats['last_error'] = str(e)
        
        time.sleep(EMAIL_POLL_INTERVAL)


# Flask API endpoints

@email_upload_bp.route('/email/health', methods=['GET'])
def health():
    """Health check endpoint for email processing."""
    return jsonify({
        'status': 'healthy' if EMAIL_UPLOAD_ENABLED else 'disabled',
        'enabled': EMAIL_UPLOAD_ENABLED,
        'last_check': stats['last_check'],
        'emails_processed_today': stats['emails_processed_today'],
        'errors_today': stats['errors_today'],
        'processor_running': stats['processor_running'],
        'last_error': stats['last_error'],
    })


@email_upload_bp.route('/email/check', methods=['POST'])
def trigger_check():
    """Manually trigger an inbox check."""
    results = check_inbox()
    return jsonify(results)


@email_upload_bp.route('/email/test', methods=['POST'])
def test_parse():
    """Test the message parser without processing a real email."""
    data = request.get_json()
    
    if not data or 'body' not in data:
        return jsonify({'error': 'Request must include "body" field'}), 400
    
    body = data['body']
    metadata = parse_t30g_message(body)
    
    if not metadata:
        return jsonify({
            'success': False,
            'error': 'No t30g tag found',
            'input': body,
        })
    
    return jsonify({
        'success': True,
        'parsed': metadata,
        'input': body,
    })


@email_upload_bp.route('/email/stats/reset', methods=['POST'])
def reset_stats():
    """Reset daily statistics."""
    global stats
    stats['emails_processed_today'] = 0
    stats['errors_today'] = 0
    return jsonify({'status': 'reset'})


def start_background_processor():
    """Start the email processor as a background thread."""
    if not EMAIL_UPLOAD_ENABLED:
        logger.info("Email upload processing is disabled")
        return
    
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Email credentials not configured, skipping email processor")
        return
    
    thread = threading.Thread(target=run_email_processor, daemon=True)
    thread.start()
    logger.info("Email processor started as background thread")


# Start background processor when module is imported (if enabled)
# Uncomment the line below to auto-start, or call start_background_processor() manually
# start_background_processor()


if __name__ == '__main__':
    # Run as standalone processor
    if not EMAIL_UPLOAD_ENABLED:
        print("EMAIL_UPLOAD_ENABLED is not set to 'true'. Set it to enable processing.")
        exit(1)
    
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        print("EMAIL_USERNAME and EMAIL_PASSWORD must be set.")
        exit(1)
    
    run_email_processor()
