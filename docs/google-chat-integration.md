# Google Chat Integration for Tom's Gym

## Overview

This document describes the integration between Google Chat and Tom's Gym that allows users to upload lifting videos by tagging messages with `t30g` in a designated Google Chat space.

**Target Space:** https://mail.google.com/mail/u/0/#chat/space/AAAAHS28PSg

---

## ⭐ Recommended Approach: Email Forwarding

**For most users, the email forwarding approach is recommended.** It works with personal Gmail accounts, is reliable, and requires no complex API setup.

**See: [google-chat-email-integration.md](./google-chat-email-integration.md)**

Quick summary:
1. User posts in Chat: `t30g 185kg Squat` + video
2. User forwards the message to `uploads@yourdomain.com`
3. Backend processes the email and uploads the video

This document covers alternative approaches including the full Chat API integration (requires Google Workspace).

---

## Quick Start Checklist (Chat API - Workspace Only)

Here's the TL;DR to get the Chat app working:

### Prerequisites (One-time setup)
- [ ] Have a Google Workspace Business/Enterprise account
- [ ] Have access to the GCP project for Tom's Gym

### GCP Console Setup (10-15 minutes)
1. [ ] Go to [Google Cloud Console](https://console.cloud.google.com)
2. [ ] Configure OAuth consent screen (APIs & Services → OAuth consent screen)
3. [ ] Enable the Google Chat API (APIs & Services → Library → Search "Chat API")
4. [ ] Go to Chat API → Configuration tab
5. [ ] Fill in: App name, Description
6. [ ] Enable: "Receive 1:1 messages" and "Join spaces and group conversations"
7. [ ] Set Connection: App URL → `https://your-backend/integrations/webhook/gchat`
8. [ ] Set Visibility: Add yourself for testing
9. [ ] Click Save

### Backend Setup
10. [ ] Create the webhook endpoint (`/integrations/webhook/gchat`)
11. [ ] Deploy or use ngrok for local testing
12. [ ] Add the bot to your Chat space
13. [ ] Test by sending a message

### Detailed Instructions Below ↓

---

## User Experience

### How Users Post Videos

Users post a message in the Google Chat space with:
1. The tag `t30g` 
2. Weight and lift type metadata
3. A video attachment

**Example messages:**
```
t30g 185kg Squat
[attached video]

t30g 315lbs Deadlift @john
[attached video]

t30g 100 Snatch
[attached video]
```

### What Happens

1. Bot detects the `t30g` tag
2. Parses weight (converts lbs to kg if needed) and lift type
3. Downloads the video attachment
4. Uploads to Tom's Gym backend with metadata
5. Replies with confirmation or error message

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Google Chat   │────▶│  Webhook Endpoint    │────▶│  Tom's Gym      │
│   Space         │     │  /integrations/      │     │  Backend        │
│   AAAAHS28PSg   │     │  webhook/gchat       │     │  /upload        │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                                  │                          │
                                  ▼                          ▼
                        ┌──────────────────┐       ┌─────────────────┐
                        │  Cloud Tasks     │       │  Google Cloud   │
                        │  (async video    │       │  Storage        │
                        │   processing)    │       │  (videos)       │
                        └──────────────────┘       └─────────────────┘
```

---

## Choosing Your Approach

### Option A: Google Workspace Chat App (Recommended if you have Workspace)

Real-time, official API, can respond in Chat. Requires Google Workspace Business/Enterprise.

### Option B: Gmail API Polling (Works with Personal Gmail)

Poll Gmail for Chat messages synced to your inbox. Works with personal accounts but not real-time.

### Option C: Browser Automation (Works with Any Account)

Use Puppeteer/Playwright to monitor Chat. Hacky but works. Against ToS.

---

## Option B: Gmail API Approach (Personal Gmail)

If you don't have Google Workspace, you can use the Gmail API to read Chat messages that are synced to Gmail.

### How It Works

1. Google Chat can sync message history to Gmail (appears under "Chats" label)
2. A script polls Gmail periodically for new messages containing `t30g`
3. When found, it parses the message and uploads to Tom's Gym

### Step 1: Enable Chat History Sync

1. Open Google Chat settings
2. Enable "Chat history" for the space
3. Messages will now appear in Gmail under the "Chats" label

### Step 2: Set Up Gmail API Access

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable the **Gmail API** (APIs & Services → Library)
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON file as `credentials.json`

### Step 3: Create the Polling Script

```python
# gmail_chat_monitor.py
import os
import time
import base64
import re
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Tom's Gym backend URL
BACKEND_URL = 'http://localhost:8080'

# Polling interval (seconds)
POLL_INTERVAL = 30

# Track processed messages
PROCESSED_FILE = 'processed_messages.txt'

def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def load_processed_ids():
    """Load set of already processed message IDs."""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_processed_id(msg_id):
    """Save a processed message ID."""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{msg_id}\n")

def parse_t30g_message(text):
    """Parse a message for t30g tag and metadata."""
    # Pattern: t30g <weight>[unit] [lift_type]
    pattern = r't30g\s+(\d+(?:\.\d+)?)\s*(kg|lbs?)?\s*(squat|bench|deadlift|snatch|clean|overhead|dl|sq|bp|sn)?'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if not match:
        return None
    
    weight = float(match.group(1))
    unit = match.group(2) or 'kg'
    lift = match.group(3) or 'snatch'
    
    # Convert lbs to kg
    if unit.lower().startswith('lb'):
        weight = round(weight * 0.453592, 2)
    
    # Normalize lift type
    lift_map = {
        'squat': 'Squat', 'sq': 'Squat',
        'bench': 'Bench', 'bp': 'Bench',
        'deadlift': 'Deadlift', 'dl': 'Deadlift',
        'snatch': 'Snatch', 'sn': 'Snatch',
        'clean': 'Clean',
        'overhead': 'Overhead'
    }
    lift_type = lift_map.get(lift.lower(), 'Snatch')
    
    return {
        'weight_kg': weight,
        'lift_type': lift_type
    }

def get_attachment_from_message(service, msg_id, attachment_id):
    """Download an attachment from a Gmail message."""
    attachment = service.users().messages().attachments().get(
        userId='me',
        messageId=msg_id,
        id=attachment_id
    ).execute()
    
    data = attachment.get('data', '')
    return base64.urlsafe_b64decode(data)

def upload_to_toms_gym(video_data, filename, metadata, user_email):
    """Upload video to Tom's Gym backend."""
    files = {
        'video': (filename, video_data, 'video/mp4')
    }
    data = {
        'weight': str(metadata['weight_kg']),
        'lift_type': metadata['lift_type'],
        'user_email': user_email,  # Backend needs to look up user
        'source': 'google_chat'
    }
    
    response = requests.post(f"{BACKEND_URL}/upload", files=files, data=data)
    return response.json()

def process_message(service, message):
    """Process a single Gmail message."""
    msg = service.users().messages().get(
        userId='me',
        id=message['id'],
        format='full'
    ).execute()
    
    # Get message body
    payload = msg.get('payload', {})
    body = ''
    
    # Handle different message structures
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    
    # Check for t30g tag
    metadata = parse_t30g_message(body)
    if not metadata:
        return None
    
    print(f"Found t30g message: {metadata}")
    
    # Look for video attachments
    video_attachment = None
    for part in payload.get('parts', []):
        if part.get('mimeType', '').startswith('video/'):
            video_attachment = part
            break
    
    if video_attachment:
        # Get sender email
        headers = {h['name']: h['value'] for h in payload.get('headers', [])}
        sender = headers.get('From', '')
        
        # Download and upload video
        attachment_data = get_attachment_from_message(
            service, 
            message['id'], 
            video_attachment['body']['attachmentId']
        )
        
        result = upload_to_toms_gym(
            attachment_data,
            video_attachment.get('filename', 'video.mp4'),
            metadata,
            sender
        )
        print(f"Uploaded: {result}")
        return result
    else:
        print("No video attachment found")
        return None

def monitor_chat():
    """Main monitoring loop."""
    print("Starting Gmail Chat monitor...")
    service = get_gmail_service()
    processed = load_processed_ids()
    
    while True:
        try:
            # Search for Chat messages with t30g
            # The "label:chats" filter gets Chat messages synced to Gmail
            results = service.users().messages().list(
                userId='me',
                q='label:chats t30g',
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg in messages:
                if msg['id'] not in processed:
                    print(f"Processing message {msg['id']}...")
                    try:
                        process_message(service, msg)
                    except Exception as e:
                        print(f"Error processing message: {e}")
                    
                    processed.add(msg['id'])
                    save_processed_id(msg['id'])
            
            print(f"[{datetime.now()}] Checked {len(messages)} messages")
            
        except Exception as e:
            print(f"Error in monitor loop: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    monitor_chat()
```

### Step 4: Run the Script

```bash
# Install dependencies
pip install google-auth-oauthlib google-api-python-client requests

# Run the monitor
python gmail_chat_monitor.py
```

On first run, it will open a browser for OAuth authentication.

### Limitations of Gmail API Approach

| Aspect | Limitation |
|--------|------------|
| **Latency** | 30+ seconds (polling delay) |
| **Real-time** | No - must poll periodically |
| **Responses** | Cannot reply in Chat |
| **Attachments** | May not sync to Gmail reliably |
| **Rate limits** | Gmail API quotas apply |

---

## Option C: Browser Automation (Playwright)

For maximum flexibility with any account type, use browser automation.

### Setup

```bash
pip install playwright
playwright install chromium
```

### Script

```python
# chat_browser_monitor.py
from playwright.sync_api import sync_playwright
import time
import re
import requests

CHAT_SPACE_URL = 'https://mail.google.com/mail/u/0/#chat/space/AAAAHS28PSg'
BACKEND_URL = 'http://localhost:8080'

def parse_t30g(text):
    """Parse t30g tag from message text."""
    pattern = r't30g\s+(\d+(?:\.\d+)?)\s*(kg|lbs?)?\s*(\w+)?'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        weight = float(match.group(1))
        if match.group(2) and match.group(2).lower().startswith('lb'):
            weight *= 0.453592
        return {
            'weight': round(weight, 2),
            'lift': match.group(3) or 'Snatch'
        }
    return None

def monitor_with_browser():
    with sync_playwright() as p:
        # Launch browser (set headless=True for background operation)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to Chat
        page.goto(CHAT_SPACE_URL)
        
        print("Please log in to Google in the browser window...")
        print("Press Enter when ready to start monitoring...")
        input()
        
        seen_messages = set()
        
        print("Monitoring for t30g messages...")
        
        while True:
            try:
                # Wait for messages to load
                page.wait_for_selector('[data-message-id]', timeout=5000)
                
                # Get all message elements
                messages = page.query_selector_all('[data-message-id]')
                
                for msg_el in messages:
                    msg_id = msg_el.get_attribute('data-message-id')
                    
                    if msg_id and msg_id not in seen_messages:
                        text = msg_el.inner_text()
                        
                        if 't30g' in text.lower():
                            parsed = parse_t30g(text)
                            if parsed:
                                print(f"Found: {parsed['weight']}kg {parsed['lift']}")
                                
                                # TODO: Handle video download
                                # This is complex - videos in Chat are not simple <video> tags
                                # You may need to click to download, then upload
                                
                        seen_messages.add(msg_id)
                
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(5)

if __name__ == '__main__':
    monitor_with_browser()
```

### ⚠️ Important Warnings

1. **Against ToS** - Browser automation of Google services violates their Terms of Service
2. **Fragile** - Google frequently changes their UI, breaking selectors
3. **Detection** - Google may detect and block automated access
4. **Resource heavy** - Requires a running browser instance

---

## Option A: Google Workspace Chat App (Official)

If you have access to Google Workspace, this is the recommended approach. See the detailed setup below.

---

## Setting Up a Google Chat App

### Important: Webhooks vs Chat Apps

**Webhooks are NOT what we need.** Webhooks in Google Chat are one-way only—they can send messages TO Chat but cannot receive messages FROM users.

For this integration, we need a **full Google Chat App** with an HTTP endpoint that can:
- Receive interaction events when users post messages
- Process the `t30g` tag and video attachments
- Respond back to the Chat space

### Prerequisites

Before you begin, you need:

1. **A Business or Enterprise Google Workspace account** with access to Google Chat
   - Personal Gmail accounts cannot create Chat apps
   - You need admin or sufficient permissions in your Workspace
   - **Alternative**: Sign up for a [14-day free Workspace trial](https://workspace.google.com/business/signup/welcome)
   
2. **A Google Cloud Project**
   - Use your existing Tom's Gym project or create a new one
   - Must be linked to your Workspace organization

3. **A publicly accessible HTTPS endpoint**
   - Your backend must be deployed with HTTPS (not HTTP)
   - For local testing, use ngrok to expose your local server

### Step 1: Create/Select a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your existing project (e.g., `toms-gym`) or create a new one
3. Note your **Project Number** (visible on the project dashboard)—you'll need this for verification

### Step 2: Configure the OAuth Consent Screen

This is required even if you're not using OAuth for users—it establishes your app's identity.

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **Internal** (for Workspace users only) or **External**
3. Fill in required fields:
   - **App name**: Tom's Gym Chat Bot
   - **User support email**: your email
   - **Developer contact information**: your email
4. Click **Save and Continue** through the scopes and test users screens
5. Click **Back to Dashboard**

### Step 3: Enable the Google Chat API

1. Go to **APIs & Services** → **Library**
2. Search for "Google Chat API"
3. Click on **Google Chat API**
4. Click **Enable**
5. Wait for it to enable (may take a few seconds)

### Step 4: Configure the Chat App

This is where you define how your Chat app works.

1. Go to **APIs & Services** → **Enabled APIs & services**
2. Click on **Google Chat API**
3. Click the **Configuration** tab (or go directly to [Chat API Configuration](https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat))
4. Fill in the configuration:

#### Basic Information

| Field | Value | Notes |
|-------|-------|-------|
| **App name** | `Tom's Gym Bot` | Max 25 characters, alphanumeric |
| **Avatar URL** | `https://your-domain.com/logo.png` | Optional, 256×256 PNG/JPEG |
| **Description** | `Upload lifting videos with t30g` | Max 40 characters |

#### Functionality

| Setting | Value |
|---------|-------|
| **Receive 1:1 messages** | ☑️ Enabled |
| **Join spaces and group conversations** | ☑️ Enabled (Required!) |

#### Connection Settings

Choose **App URL** (HTTP endpoint) and enter:

```
https://your-backend-url.com/integrations/webhook/gchat
```

**For local development**, use ngrok:
```bash
# Terminal 1: Start your backend
./run-dev.sh local

# Terminal 2: Expose with ngrok
ngrok http 8080

# Use the ngrok URL: https://abc123.ngrok.io/integrations/webhook/gchat
```

#### Visibility (Who Can Use the App)

For testing, you have two options:

**Option A: Specific People (Recommended for initial testing)**
- Select "Make this Chat app available to specific people and groups"
- Add up to 5 email addresses (yourself and testers)
- These users can immediately find and use your app

**Option B: Domain-wide**
- Select "Make this Chat app available to everyone in [your domain]"
- All users in your Workspace can use the app

### Step 5: Save and Test

1. Click **Save**
2. Your app is now registered but in "Draft" status
3. Users listed in Visibility can find and use the app immediately

### Step 6: Add the Bot to Your Chat Space

1. Open Google Chat: https://chat.google.com
2. Go to your space (or the one at `AAAAHS28PSg`)
3. Click the space name at the top → **Manage apps & integrations**
4. Search for "Tom's Gym Bot" (your app name)
5. Click **Add** or **Add to space**
6. The bot should send an `ADDED_TO_SPACE` event to your endpoint

### Step 7: Verify Events Are Received

Test that your endpoint receives events:

1. In the Chat space, send a test message: `Hello @Tom's Gym Bot`
2. Check your backend logs for the incoming request
3. You should see a `MESSAGE` event with the message content

---

## How the Chat App Receives Messages

### Important: Your App Receives ALL Messages in the Space

Once your Chat app is added to a space, it receives a `MESSAGE` event for **every message** posted in that space—not just @mentions. This is ideal for the `t30g` tag detection since users don't need to @mention the bot.

### Event Flow

```
User posts: "t30g 185kg Squat" + video attachment
                    ↓
Google Chat sends HTTP POST to your endpoint
                    ↓
Your endpoint receives JSON event payload
                    ↓
Parse message for t30g tag
                    ↓
If found: download video, upload to Tom's Gym
                    ↓
Return JSON response (shown in Chat)
```

### Request/Response Timing

- **Synchronous response**: Must respond within **30 seconds**
- **Asynchronous response**: For longer operations, acknowledge immediately and use the Chat API to send a follow-up message

---

## Connection Settings Options

Google Chat apps support four different connection methods. Here's when to use each:

### Option 1: HTTP Endpoint URL (Recommended for Tom's Gym)

**Best for**: Existing backend services, full control over infrastructure

```
Connection type: App URL
URL: https://your-backend.com/integrations/webhook/gchat
```

**Pros**:
- Integrates directly with your existing Flask backend
- Full control over processing logic
- Can access your database directly

**Cons**:
- Requires a publicly accessible HTTPS endpoint
- Need to handle verification and security yourself

### Option 2: Google Apps Script

**Best for**: Simple bots, quick prototypes, no infrastructure to manage

```javascript
// Code.gs
function onMessage(event) {
  const text = event.message.text || '';
  if (text.includes('t30g')) {
    // Process and forward to your backend
    return { text: 'Processing your video...' };
  }
}
```

**Pros**:
- No server needed—runs on Google's infrastructure
- Easy to deploy and update
- Built-in Google service authentication

**Cons**:
- Limited execution time (6 minutes max)
- Less control over environment
- Harder to debug

### Option 3: Cloud Pub/Sub

**Best for**: High-volume apps, decoupled architecture, reliability

```
Connection type: Cloud Pub/Sub topic name
Topic: projects/your-project/topics/chat-events
```

**Pros**:
- Decoupled from your main backend
- Built-in retry and delivery guarantees
- Can scale independently

**Cons**:
- More complex setup
- Additional GCP costs
- Requires Pub/Sub subscription handler

### Option 4: Dialogflow

**Best for**: Natural language understanding, complex conversations

**Pros**:
- Built-in NLU capabilities
- Easy to handle varied phrasings

**Cons**:
- Overkill for simple tag detection
- Additional complexity

---

## Local Development Setup

### Using ngrok for Testing

Since Google Chat requires HTTPS, you need to expose your local development server.

#### Step 1: Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

#### Step 2: Start Your Backend

```bash
# Using Docker (recommended)
./run-dev.sh local

# Or directly
cd Backend && python -m flask run --port 8080
```

#### Step 3: Expose with ngrok

```bash
ngrok http 8080
```

You'll see output like:
```
Session Status                online
Forwarding                    https://a1b2c3d4.ngrok.io -> http://localhost:8080
```

#### Step 4: Update Chat App Configuration

1. Go to [Chat API Configuration](https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat)
2. Update the App URL to your ngrok URL:
   ```
   https://a1b2c3d4.ngrok.io/integrations/webhook/gchat
   ```
3. Click **Save**

#### Step 5: Test

Send a message in your Chat space—you should see the request in your local terminal.

**Note**: ngrok URLs change each time you restart. For persistent URLs, use ngrok's paid plans or deploy to a staging environment.

---

## Authentication & Security

### Verifying Requests from Google Chat

Google Chat sends a bearer token with each request. Verify it to ensure requests are legitimate.

**Method 1: Bearer Token Verification**

```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

CHAT_ISSUER = 'chat@system.gserviceaccount.com'
YOUR_PROJECT_NUMBER = '123456789'  # From GCP Console

def verify_google_chat_request(request):
    """Verify the request came from Google Chat."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    try:
        # Verify the token
        claims = id_token.verify_token(
            token,
            google_requests.Request(),
            audience=YOUR_PROJECT_NUMBER
        )
        
        # Check the issuer
        if claims.get('iss') != CHAT_ISSUER:
            return False
            
        return True
    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        return False
```

**Method 2: Space Restriction (Simpler)**

```python
ALLOWED_SPACE = 'spaces/AAAAHS28PSg'

def is_allowed_space(event):
    space = event.get('space', {}).get('name', '')
    return space == ALLOWED_SPACE
```

### Service Account Setup

For downloading attachments and sending responses, you need a service account:

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Name: `toms-gym-chat-bot`
4. Grant role: **Chat Bots** (or custom role with `chat.messages.create`)
5. Click **Done**
6. Click on the service account → **Keys** → **Add Key** → **Create new key** → **JSON**
7. Save the JSON file securely (add to `.gitignore`!)

---

## Event Types from Google Chat

### MESSAGE Event

Sent when a user posts a message in a space where the bot is present.

```json
{
  "type": "MESSAGE",
  "eventTime": "2024-01-15T10:30:00.000Z",
  "message": {
    "name": "spaces/AAAAHS28PSg/messages/abc123",
    "sender": {
      "name": "users/123456789",
      "displayName": "John Smith",
      "email": "john@example.com",
      "type": "HUMAN"
    },
    "createTime": "2024-01-15T10:30:00.000Z",
    "text": "t30g 185kg Squat",
    "thread": {
      "name": "spaces/AAAAHS28PSg/threads/xyz789"
    },
    "space": {
      "name": "spaces/AAAAHS28PSg",
      "type": "ROOM"
    },
    "attachment": [
      {
        "name": "spaces/AAAAHS28PSg/messages/abc123/attachments/att001",
        "contentName": "lift_video.mp4",
        "contentType": "video/mp4",
        "attachmentDataRef": {
          "resourceName": "media/download/...",
          "attachmentDataRefUri": "https://chat.googleapis.com/v1/media/..."
        },
        "source": "UPLOADED_CONTENT"
      }
    ]
  },
  "user": {
    "name": "users/123456789",
    "displayName": "John Smith",
    "email": "john@example.com",
    "type": "HUMAN"
  },
  "space": {
    "name": "spaces/AAAAHS28PSg",
    "type": "ROOM",
    "displayName": "Tom's Gym Lifts"
  }
}
```

### ADDED_TO_SPACE Event

Sent when the bot is added to a space.

```json
{
  "type": "ADDED_TO_SPACE",
  "eventTime": "2024-01-15T10:00:00.000Z",
  "space": {
    "name": "spaces/AAAAHS28PSg",
    "type": "ROOM",
    "displayName": "Tom's Gym Lifts"
  },
  "user": {
    "name": "users/123456789",
    "displayName": "Admin User",
    "email": "admin@example.com"
  }
}
```

### REMOVED_FROM_SPACE Event

Sent when the bot is removed from a space.

```json
{
  "type": "REMOVED_FROM_SPACE",
  "eventTime": "2024-01-15T11:00:00.000Z",
  "space": {
    "name": "spaces/AAAAHS28PSg"
  }
}
```

---

## Downloading Video Attachments

Video attachments require authentication to download.

### Using the Chat API

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io

SCOPES = ['https://www.googleapis.com/auth/chat.bot']
SERVICE_ACCOUNT_FILE = 'path/to/service-account.json'

def download_attachment(attachment_data_ref: dict) -> bytes:
    """
    Download an attachment from Google Chat.
    
    Args:
        attachment_data_ref: The attachmentDataRef object from the message
        
    Returns:
        The attachment content as bytes
    """
    # Create credentials
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    
    # Build the Chat API service
    service = build('chat', 'v1', credentials=credentials)
    
    # Get the media download URI
    resource_name = attachment_data_ref.get('resourceName')
    
    # Download the media
    request = service.media().download(resourceName=resource_name)
    
    # Execute and get content
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    return file_content.getvalue()
```

### Alternative: Direct URL with OAuth Token

```python
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def download_attachment_direct(download_uri: str) -> bytes:
    """Download attachment using direct URI with OAuth."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    credentials.refresh(Request())
    
    headers = {
        'Authorization': f'Bearer {credentials.token}'
    }
    
    response = requests.get(download_uri, headers=headers)
    response.raise_for_status()
    
    return response.content
```

---

## Sending Responses

### Simple Text Response

Return a JSON object from your webhook:

```python
@gchat_bp.route('/webhook/gchat', methods=['POST'])
def webhook():
    # ... process message ...
    
    return jsonify({
        'text': '✅ Video uploaded successfully! 185kg Squat'
    })
```

### Rich Card Response

```python
def create_upload_success_card(weight, lift_type, video_url):
    return {
        'cards': [{
            'header': {
                'title': 'Video Uploaded! 🏋️',
                'subtitle': f'{weight}kg {lift_type}'
            },
            'sections': [{
                'widgets': [
                    {
                        'textParagraph': {
                            'text': f'Your lift has been added to the competition.'
                        }
                    },
                    {
                        'buttons': [{
                            'textButton': {
                                'text': 'VIEW IN APP',
                                'onClick': {
                                    'openLink': {
                                        'url': video_url
                                    }
                                }
                            }
                        }]
                    }
                ]
            }]
        }]
    }
```

---

## Message Parsing Specification

### Tag Format

The tag `t30g` must appear in the message (case-insensitive).

### Metadata Extraction

**Pattern:** `t30g <weight>[unit] [lift_type] [@username]`

| Component | Required | Format | Default |
|-----------|----------|--------|---------|
| `t30g` | Yes | Literal | - |
| `weight` | Yes | Number (int or decimal) | - |
| `unit` | No | `kg`, `lbs`, `lb` | `kg` |
| `lift_type` | No | See below | `Snatch` |
| `@username` | No | @mention | Sender |

### Supported Lift Types

| Input (case-insensitive) | Maps to |
|--------------------------|---------|
| `squat`, `sq` | Squat |
| `bench`, `bp` | Bench |
| `deadlift`, `dl` | Deadlift |
| `snatch`, `sn` | Snatch |
| `clean`, `c&j`, `cj`, `cleanandjerk` | Clean |
| `overhead`, `ohp`, `press` | Overhead |

### Examples

| Message | Parsed Weight | Parsed Lift |
|---------|---------------|-------------|
| `t30g 185kg Squat` | 185 kg | Squat |
| `t30g 315lbs deadlift` | 142.88 kg | Deadlift |
| `t30g 100 sn` | 100 kg | Snatch |
| `t30g 60` | 60 kg | Snatch (default) |
| `Check out my t30g 200kg dl!` | 200 kg | Deadlift |

---

## Testing the Integration

### Local Development with ngrok

1. Install ngrok: `brew install ngrok` (macOS)
2. Start your backend locally: `./run-dev.sh local`
3. Expose with ngrok: `ngrok http 8080`
4. Use the ngrok URL in Google Chat app configuration

### Test Messages

Send these in your Chat space to test:

```
# Basic test
t30g 100kg Squat

# With pounds
t30g 225lbs bench

# Minimal
t30g 80

# In a sentence
Just hit a new PR! t30g 200kg deadlift 💪
```

### Verify Webhook Receives Events

Add logging to see incoming events:

```python
@gchat_bp.route('/webhook/gchat', methods=['POST'])
def webhook():
    event = request.get_json()
    logger.info(f"Received Google Chat event: {json.dumps(event, indent=2)}")
    # ...
```

---

## Implementation Checklist

### Phase 1: Basic Setup
- [ ] Enable Google Chat API in GCP
- [ ] Create and configure Chat app
- [ ] Add webhook endpoint to backend
- [ ] Deploy and test with ngrok locally
- [ ] Verify events are received

### Phase 2: Message Processing
- [ ] Implement message parsing for `t30g` tag
- [ ] Extract weight and lift type
- [ ] Handle unit conversion (lbs → kg)
- [ ] Add response messages

### Phase 3: Video Upload
- [ ] Set up service account for Chat API
- [ ] Implement attachment download
- [ ] Connect to existing `/upload` endpoint
- [ ] Add user lookup by email

### Phase 4: Production Hardening
- [ ] Add request verification
- [ ] Implement async processing with Cloud Tasks
- [ ] Add error handling and retries
- [ ] Add rate limiting
- [ ] Monitor and log uploads

---

## Environment Variables

Add to your backend configuration:

```bash
# Google Chat Integration
GOOGLE_CHAT_PROJECT_NUMBER=123456789
GOOGLE_CHAT_SERVICE_ACCOUNT=/path/to/service-account.json
GOOGLE_CHAT_ALLOWED_SPACE=spaces/AAAAHS28PSg
GOOGLE_CHAT_ENABLED=true
```

---

## Troubleshooting

### Chat App Registration Issues

#### "You don't have permission to configure this API"
- Ensure you're using a Google Workspace account (not personal Gmail)
- You need to be an owner or editor of the GCP project
- Ask your Workspace admin for permissions if needed

#### "OAuth consent screen not configured"
- Go to APIs & Services → OAuth consent screen
- Complete the basic configuration (even if minimal)
- You don't need to add scopes for receiving events

#### App doesn't appear in Chat search
- Check Visibility settings—you must be listed or in the allowed domain
- Wait a few minutes after saving (propagation delay)
- Try searching by exact app name
- Clear browser cache and refresh Chat

#### "Invalid URL" when saving configuration
- URL must start with `https://` (not `http://`)
- URL must be publicly accessible (not localhost)
- For local dev, use ngrok or similar tunneling service

### Bot Not Receiving Messages

#### No requests hitting your endpoint
1. **Check the endpoint URL** in Chat API Configuration
2. **Verify HTTPS** - Google Chat only sends to HTTPS endpoints
3. **Test endpoint directly**:
   ```bash
   curl -X POST https://your-url/integrations/webhook/gchat \
     -H "Content-Type: application/json" \
     -d '{"type": "TEST"}'
   ```
4. **Check firewall/security groups** if on cloud infrastructure
5. **Review Cloud Logging** in GCP for Chat API errors

#### Bot added but not receiving MESSAGE events
- Ensure **"Join spaces and group conversations"** is enabled in configuration
- The bot receives messages **only after** it's added to the space
- Check if another error is occurring (look at backend logs)

#### Receiving ADDED_TO_SPACE but not MESSAGE events
- This is normal if the app isn't @mentioned
- Verify your endpoint handles all event types
- Check the `type` field in incoming requests

### Request Verification Issues

#### "Token verification failed"
- Ensure you're using the correct Project Number (not Project ID)
- The issuer should be `chat@system.gserviceaccount.com`
- Check your system clock is accurate (tokens are time-sensitive)

### Attachment/Video Download Issues

#### "403 Forbidden" when downloading attachment
- Service account needs Chat API permissions
- Ensure the service account JSON file is correctly loaded
- Verify Chat API scope is included: `https://www.googleapis.com/auth/chat.bot`

#### "Attachment not found"
- Attachments expire after some time
- Process videos quickly after receiving the event
- Consider downloading to Cloud Storage immediately

### User Not Found in Database

#### Email mismatch
- Google Chat email might differ from Tom's Gym registration email
- Consider adding an email alias mapping table
- Fallback: prompt user to link their account

#### Creating users automatically
- Could auto-create user records for unknown Chat users
- Send a message asking them to complete registration

### Common Error Responses

| HTTP Status | Meaning | Solution |
|-------------|---------|----------|
| 400 | Bad request | Check your response JSON format |
| 401 | Unauthorized | Verify token if implementing auth |
| 403 | Forbidden | Check API permissions and quotas |
| 404 | Not found | Verify endpoint URL path |
| 500 | Server error | Check your backend logs |
| 503 | Service unavailable | Backend might be down or overloaded |

### Debugging Tips

1. **Add detailed logging** to your webhook endpoint:
   ```python
   @gchat_bp.route('/webhook/gchat', methods=['POST'])
   def webhook():
       logger.info(f"Headers: {dict(request.headers)}")
       logger.info(f"Body: {request.get_json()}")
       # ... rest of handler
   ```

2. **Use the Chat API Explorer** to test API calls:
   https://developers.google.com/workspace/chat/api/reference

3. **Check Cloud Logging** for Chat API errors:
   - Go to GCP Console → Logging → Logs Explorer
   - Filter by resource type "Google Chat API"

4. **Test with minimal response** first:
   ```python
   return jsonify({'text': 'Received!'})
   ```

---

## References

- [Google Chat API Documentation](https://developers.google.com/chat)
- [Chat App Configuration](https://developers.google.com/chat/how-tos/apps-publish)
- [Chat Events Reference](https://developers.google.com/chat/api/reference/rest/v1/spaces.messages)
- [Chat Cards & Dialogs](https://developers.google.com/chat/ui/cards-overview)
