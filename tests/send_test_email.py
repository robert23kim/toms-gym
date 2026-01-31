#!/usr/bin/env python3
"""
Test script to send emails with video attachments to the Tom's Gym email upload system.

Usage:
    # With t30g tag:
    python tests/send_test_email.py --video tests/data/output_deadlift.mp4 --body "t30g 100kg Squat"

    # Without t30g tag (uses competition defaults):
    python tests/send_test_email.py --video tests/data/output_deadlift.mp4
    
    # Specify different recipient or sender:
    python tests/send_test_email.py --video tests/data/output_deadlift.mp4 --to t30gupload@gmail.com

Environment variables (from Backend/.env):
    EMAIL_USERNAME: The email account to send from
    EMAIL_PASSWORD: The app password for the email account
    EMAIL_SMTP_SERVER: SMTP server (default: smtp.gmail.com)
    EMAIL_SMTP_PORT: SMTP port (default: 587)
"""

import os
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# Try to load environment variables from Backend/.env
def load_env():
    env_file = Path(__file__).parent.parent / 'Backend' / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Don't override existing environment variables
                    if key not in os.environ:
                        os.environ[key] = value


def send_email_with_video(
    to_email: str,
    subject: str,
    body: str,
    video_path: str,
    from_email: str = None,
    smtp_server: str = None,
    smtp_port: int = None,
    username: str = None,
    password: str = None,
) -> bool:
    """
    Send an email with a video attachment.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        video_path: Path to the video file to attach
        from_email: Sender email (defaults to EMAIL_USERNAME)
        smtp_server: SMTP server (defaults to EMAIL_SMTP_SERVER or smtp.gmail.com)
        smtp_port: SMTP port (defaults to EMAIL_SMTP_PORT or 587)
        username: SMTP username (defaults to EMAIL_USERNAME)
        password: SMTP password (defaults to EMAIL_PASSWORD)
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    # Get configuration from environment
    from_email = from_email or os.environ.get('EMAIL_USERNAME')
    smtp_server = smtp_server or os.environ.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = smtp_port or int(os.environ.get('EMAIL_SMTP_PORT', '587'))
    username = username or os.environ.get('EMAIL_USERNAME')
    password = password or os.environ.get('EMAIL_PASSWORD')
    
    if not username or not password:
        print("Error: EMAIL_USERNAME and EMAIL_PASSWORD must be set")
        print("Set them in environment or Backend/.env file")
        return False
    
    if not from_email:
        from_email = username
    
    # Check video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Attach body
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach video
    video_filename = os.path.basename(video_path)
    video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    
    print(f"Attaching video: {video_filename} ({video_size_mb:.2f} MB)")
    
    with open(video_path, 'rb') as f:
        video_data = f.read()
    
    # Determine MIME type
    ext = os.path.splitext(video_path)[1].lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
    }
    mime_type = mime_types.get(ext, 'video/mp4')
    
    attachment = MIMEBase(*mime_type.split('/'))
    attachment.set_payload(video_data)
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', f'attachment; filename="{video_filename}"')
    msg.attach(attachment)
    
    # Send email
    try:
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            print(f"Logging in as {username}...")
            server.login(username, password)
            print(f"Sending email to {to_email}...")
            server.send_message(msg)
        
        print(f"✅ Email sent successfully!")
        print(f"   From: {from_email}")
        print(f"   To: {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body: {body[:100]}..." if len(body) > 100 else f"   Body: {body}")
        print(f"   Video: {video_filename}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Make sure you're using an App Password, not your regular password")
        return False
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Send test email with video attachment to Tom\'s Gym upload system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send with t30g tag:
  python tests/send_test_email.py --video tests/data/output_deadlift.mp4 --body "t30g 100kg Squat"

  # Send without t30g tag (uses competition defaults):
  python tests/send_test_email.py --video tests/data/output_deadlift.mp4

  # Send to a specific email:
  python tests/send_test_email.py --video tests/data/output_deadlift.mp4 --to t30gupload@gmail.com
        """
    )
    
    parser.add_argument(
        '--video', '-v',
        required=True,
        help='Path to video file to attach'
    )
    parser.add_argument(
        '--to', '-t',
        default='t30gupload@gmail.com',
        help='Recipient email address (default: t30gupload@gmail.com)'
    )
    parser.add_argument(
        '--subject', '-s',
        default='Test upload',
        help='Email subject (default: "Test upload")'
    )
    parser.add_argument(
        '--body', '-b',
        default='Testing email upload without t30g tag - should use competition defaults',
        help='Email body text. Include "t30g <weight> <lift>" to specify lift details'
    )
    parser.add_argument(
        '--from', '-f',
        dest='from_email',
        help='Sender email address (default: EMAIL_USERNAME from env)'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_env()
    
    # Send the email
    success = send_email_with_video(
        to_email=args.to,
        subject=args.subject,
        body=args.body,
        video_path=args.video,
        from_email=args.from_email,
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
