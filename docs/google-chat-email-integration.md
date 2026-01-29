# Google Chat Integration via Email Forwarding

## Overview

This document describes the email-based integration between Google Chat and Tom's Gym. Users post videos in Google Chat with metadata, then forward the message to a dedicated email address for processing.

**Why this approach?**
- Works with personal Gmail accounts (no Workspace required)
- Reliable and predictable timing (~2 minutes)
- Simple implementation
- No complex API authentication

---

## User Workflow

### Step 1: Post in Google Chat

User posts a message in the Chat space with:
- The tag `t30g`
- Weight and lift type
- Video attachment

**Example message:**
```
t30g 185kg Squat
[video attached]
```

### Step 2: Forward to Email

1. **On mobile**: Long-press the message → **Forward** → **Email**
2. **On desktop**: Click the three dots (⋮) on the message → **Forward to inbox**
3. Send to: `uploads@yourdomain.com`

### Step 3: Confirmation

Within a few minutes, the user receives:
- Email confirmation of successful upload
- Or error message if something went wrong

---

## Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│   Google Chat   │                    │   Tom's Gym     │
│   Space         │                    │   Frontend      │
└────────┬────────┘                    └─────────────────┘
         │                                      ▲
         │ Forward (manual)                     │
         ▼                                      │
┌─────────────────┐     Poll/Push      ┌───────┴─────────┐
│   Email Inbox   │ ──────────────────▶│   Tom's Gym     │
│ uploads@domain  │    (every 30s)     │   Backend       │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │  Google Cloud   │
                                       │  Storage        │
                                       └─────────────────┘
```

---

## Setup Guide

### Part 1: Email Inbox Setup

You have several options for the email inbox:

#### Option A: Gmail with App Password (Recommended for testing)

1. **Create or use a Gmail account** for uploads (e.g., `tomsgym.uploads@gmail.com`)

2. **Enable 2-Factor Authentication**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification

3. **Create an App Password**:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select app: "Mail"
   - Select device: "Other" → name it "Tom's Gym Backend"
   - Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

4. **Enable IMAP**:
   - Go to Gmail Settings → See all settings → Forwarding and POP/IMAP
   - Enable IMAP
   - Save changes

#### Option B: Custom Domain Email (Recommended for production)

Use your domain's email (e.g., `uploads@tomsgym.com`) via:
- Google Workspace
- Zoho Mail (free tier available)
- Fastmail
- Any IMAP-compatible provider

#### Option C: SendGrid/Mailgun Inbound Parse (Advanced)

These services can POST incoming emails directly to your webhook:
- No polling required
- Real-time processing
- More complex setup

---

### Part 2: Environment Configuration

Add these environment variables to your backend:

```bash
# .env or environment configuration

# Email Processing
EMAIL_UPLOAD_ENABLED=true
EMAIL_UPLOAD_ADDRESS=uploads@yourdomain.com
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=tomsgym.uploads@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop  # App password, no spaces
EMAIL_POLL_INTERVAL=30  # seconds

# Optional: Send confirmation emails
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SEND_CONFIRMATIONS=true
```

---

### Part 3: Backend Implementation

Create the email processing module at `Backend/toms_gym/integrations/email_upload.py`.

See the implementation in the codebase.

---

### Part 4: Register the Blueprint

Add to `Backend/toms_gym/app.py`:

```python
from toms_gym.integrations.email_upload import email_upload_bp

app.register_blueprint(email_upload_bp, url_prefix='/integrations')
```

---

### Part 5: Run the Email Processor

#### Option A: Background Thread (Simple)

The processor starts automatically when the Flask app starts if `EMAIL_UPLOAD_ENABLED=true`.

#### Option B: Separate Worker (Production)

Run as a separate process:

```bash
python -m toms_gym.integrations.email_upload
```

#### Option C: Cron Job

Add to crontab:

```bash
# Check for uploads every minute
* * * * * cd /path/to/backend && python -c "from toms_gym.integrations.email_upload import check_inbox; check_inbox()"
```

---

## Message Format Specification

### Supported Formats

The parser is flexible and handles various message formats:

```
# Standard format
t30g 185kg Squat

# With pounds (auto-converts to kg)
t30g 315lbs Deadlift

# Minimal (defaults to kg and Snatch)
t30g 100

# In a sentence
Just hit a new PR! t30g 200kg deadlift 💪

# With user mention
t30g 185kg Squat @john
```

### Metadata Extraction

| Field | Pattern | Default |
|-------|---------|---------|
| Weight | Number after `t30g` | Required |
| Unit | `kg`, `lbs`, `lb` after number | `kg` |
| Lift Type | Word after unit | `Snatch` |

### Supported Lift Types

| Input (case-insensitive) | Maps to |
|--------------------------|---------|
| `squat`, `sq` | Squat |
| `bench`, `bp` | Bench |
| `deadlift`, `dl` | Deadlift |
| `snatch`, `sn` | Snatch |
| `clean`, `c&j`, `cj` | Clean |
| `overhead`, `ohp`, `press` | Overhead |

---

## Forwarded Email Structure

When a user forwards a Chat message to email, it typically looks like:

```
From: user@gmail.com
To: uploads@yourdomain.com
Subject: Fwd: Google Chat message

---------- Forwarded message ---------
From: John Smith <john@example.com>
Date: Mon, Jan 15, 2024 at 10:30 AM
Subject: 

t30g 185kg Squat

[Video attachment: lift_video.mp4]
```

The parser handles:
- Forwarded message headers
- Original sender extraction
- Body text parsing
- Video attachment extraction

---

## Video Attachment Handling

### Supported Formats

| Extension | MIME Type |
|-----------|-----------|
| `.mp4` | `video/mp4` |
| `.mov` | `video/quicktime` |
| `.avi` | `video/x-msvideo` |
| `.mkv` | `video/x-matroska` |
| `.webm` | `video/webm` |

### Size Limits

- Gmail attachment limit: **25 MB**
- For larger videos, Google Chat may convert to a Drive link (not currently supported)

### Processing Flow

```
Email received
     ↓
Extract video attachment
     ↓
Save to temp file
     ↓
Upload to GCS via /upload endpoint
     ↓
Create Attempt record in database
     ↓
Delete temp file
     ↓
Send confirmation email
```

---

## User Lookup

The system matches users by email address:

1. **Direct match**: Email matches `User.email` in database
2. **Forwarded sender**: Extract original sender from forwarded message
3. **Fallback**: Use the person who forwarded the email

### If User Not Found

Options (configurable):
- **Reject**: Send error email asking user to register
- **Create**: Auto-create user account
- **Default**: Assign to a default/anonymous user

---

## Error Handling

### Common Errors

| Error | User Message | Resolution |
|-------|--------------|------------|
| No `t30g` tag | "Could not find t30g tag in message" | User re-forwards with tag |
| No video attachment | "No video file attached" | User re-forwards with video |
| User not found | "Please register at tomsgym.com first" | User creates account |
| Invalid lift type | "Unknown lift type 'X', using Snatch" | Auto-fallback |
| Video too large | "Video exceeds 25MB limit" | User compresses video |

### Error Notifications

When processing fails, the system:
1. Logs the error
2. Sends an email to the user explaining the issue
3. Optionally notifies admins

---

## Monitoring & Debugging

### Logs

Email processing logs to `email_upload.log`:

```
2024-01-15 10:30:00 INFO Processing email from user@gmail.com
2024-01-15 10:30:01 INFO Found t30g tag: 185kg Squat
2024-01-15 10:30:02 INFO Video attachment: lift_video.mp4 (15.2 MB)
2024-01-15 10:30:05 INFO Upload successful: attempt_id=abc123
2024-01-15 10:30:05 INFO Confirmation sent to user@gmail.com
```

### Health Check Endpoint

```bash
curl http://localhost:8080/integrations/email/health
```

Returns:
```json
{
  "status": "healthy",
  "last_check": "2024-01-15T10:30:00Z",
  "emails_processed_today": 12,
  "errors_today": 1
}
```

### Manual Processing

Trigger a manual inbox check:

```bash
curl -X POST http://localhost:8080/integrations/email/check
```

---

## Testing

### Test Email Locally

1. Start the backend with email processing enabled
2. Send a test email to the uploads address:
   ```
   To: uploads@yourdomain.com
   Subject: Test upload
   
   t30g 100kg Squat
   
   [Attach a test video]
   ```
3. Check logs for processing
4. Verify video appears in the app

### Test Without Real Email

Use the test endpoint:

```bash
curl -X POST http://localhost:8080/integrations/email/test \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "body": "t30g 185kg Squat",
    "has_video": true
  }'
```

---

## Security Considerations

### Email Spoofing

Anyone can send email claiming to be from any address. Mitigations:
- Verify sender is a registered user
- Require email verification during registration
- Consider SPF/DKIM checking (advanced)

### Rate Limiting

Prevent abuse:
- Limit uploads per user per day
- Limit total email processing rate
- Block repeated failures from same sender

### Attachment Scanning

Consider:
- File type verification (magic bytes, not just extension)
- Virus scanning for uploaded files
- Size limits strictly enforced

---

## Production Checklist

- [ ] Dedicated email address created
- [ ] App password or OAuth configured
- [ ] IMAP access enabled
- [ ] Environment variables set
- [ ] Email processor running (thread, worker, or cron)
- [ ] Monitoring/alerting configured
- [ ] Error notification emails working
- [ ] User documentation published
- [ ] Rate limiting configured
- [ ] Logs being collected

---

## Comparison with Other Approaches

| Aspect | Email Forward | Chat API | Chat App Webhook |
|--------|---------------|----------|------------------|
| Personal Gmail | ✅ Yes | ❌ No | ❌ No |
| Workspace | ✅ Yes | ✅ Yes | ✅ Yes |
| Latency | ~2-3 min | ~5 sec | Real-time |
| Reliability | High | High | High |
| User effort | 2 taps | None | None |
| Implementation | Medium | Medium | Medium |
| Can respond in Chat | ❌ No | ✅ Yes | ✅ Yes |
| Cost | Free | $6/mo min | $6/mo min |

---

## Future Enhancements

1. **SendGrid/Mailgun webhook**: Real-time email processing without polling
2. **Google Drive links**: Handle videos shared as Drive links
3. **Multiple spaces**: Support different email addresses per Chat space
4. **Confirmation in Chat**: If Workspace, post confirmation back to Chat
5. **Edit support**: Allow re-processing if user forwards a correction
