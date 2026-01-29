# Google Chat Integration via Email Forwarding

## Overview

This document describes the email-based integration between Google Chat and Tom's Gym. Users post videos in Google Chat with metadata, then forward the message to a dedicated email address for processing.

**Status:** ✅ **Implemented and Tested** (January 2026)

**Upload Email:** `t30gupload@gmail.com`

**Why this approach?**
- Works with personal Gmail accounts (no Workspace required)
- Reliable and predictable timing (~30 seconds polling)
- Simple implementation
- No complex API authentication
- Confirmation emails include direct link to uploaded video

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
- Email confirmation of successful upload with **direct link to the video**
- Or error message if something went wrong

**Example Success Email:**
```
Subject: ✅ Tom's Gym - Video Uploaded Successfully

Your video has been uploaded to Tom's Gym!

Details:
- Weight: 100 kg
- Lift Type: Snatch
- Attempt ID: abc123-def456

🎬 Watch your video:
https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/videos/20260129_193039_video.mp4

View your lift in the app: https://tomsgym.com

Thanks for sharing your lift! 💪
```

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

#### Option A: Gmail with App Password (Currently Implemented ✅)

**Current Setup:** `t30gupload@gmail.com`

1. **Create or use a Gmail account** for uploads
   - We created: `t30gupload@gmail.com`

2. **Enable 2-Factor Authentication**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification

3. **Create an App Password**:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select app: "Mail"
   - Select device: "Other" → name it "Tom's Gym Backend"
   - Copy the 16-character password (format: `abcd efgh ijkl mnop`)
   - **Note:** Store without spaces in environment variable

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

Add these environment variables to your backend. These are configured in `docker-compose.yml` and `docker-compose.override.yml`:

```bash
# .env or docker-compose.yml environment section

# Email Processing - Enable/disable the feature
EMAIL_UPLOAD_ENABLED=true

# IMAP settings (for reading incoming emails)
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=t30gupload@gmail.com
EMAIL_PASSWORD=${EMAIL_APP_PASSWORD}  # App password, no spaces
EMAIL_POLL_INTERVAL=30  # seconds between inbox checks

# SMTP settings (for sending confirmation emails)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SEND_CONFIRMATIONS=true

# Backend URL for internal API calls
BACKEND_URL=http://localhost:8080

# Frontend URL for email links
FRONTEND_URL=https://tomsgym.com
```

**Security Note:** Store the app password in an environment variable (`EMAIL_APP_PASSWORD`) rather than hardcoding it in docker-compose files.

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

### Tested Workflow (January 2026)

The following workflow has been verified end-to-end:

1. **Send email** to `t30gupload@gmail.com` with:
   - Body: `t30g 100kg Snatch` (or other valid lift type)
   - Attachment: Video file (MP4, MOV, etc. up to 25MB)

2. **Backend processes** within 30 seconds:
   - Email is detected via IMAP polling
   - Video is uploaded to Google Cloud Storage
   - Attempt record is created in database
   - Confirmation email is sent with video link

3. **Example successful log output:**
   ```
   INFO:toms_gym.integrations.email_upload:Processing email from toka778@gmail.com
   INFO:toms_gym.integrations.email_upload:Found t30g tag: 100.0kg Snatch
   INFO:toms_gym.integrations.email_upload:Video attachment: output_video.mp4 (13.86 MB)
   INFO:toms_gym.routes.upload_routes:=== UPLOAD VIDEO FUNCTION COMPLETED ===
   INFO:toms_gym.integrations.email_upload:Confirmation email sent to toka778@gmail.com
   ```

### Test Email Locally

1. Start the backend with Docker:
   ```bash
   docker-compose up -d --build
   ```

2. Send a test email to `t30gupload@gmail.com`:
   ```
   To: t30gupload@gmail.com
   Subject: Test upload
   
   t30g 100kg Snatch
   
   [Attach a test video]
   ```

3. Check logs for processing:
   ```bash
   docker logs toms-gym-backend -f
   ```

4. Verify video appears in GCS bucket

### Test Endpoints

```bash
# Check health
curl http://localhost:8080/integrations/email/health

# Manually trigger inbox check
curl -X POST http://localhost:8080/integrations/email/check

# Reset stats
curl -X POST http://localhost:8080/integrations/email/stats/reset
```

### Test Without Real Email

Use the test endpoint:

```bash
curl -X POST http://localhost:8080/integrations/email/test \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "body": "t30g 185kg Snatch",
    "has_video": true
  }'
```

---

## Known Issues & Lessons Learned

### Database Enum Constraints

The Tom's Gym database uses PostgreSQL enums for `lift_type` and `weight_class`. When testing locally, you may encounter errors if the enum values don't match:

**Lift Type Enum (production may differ):**
- `snatch`
- `clean_and_jerk`

**Weight Class Enum:**
- `56kg`, `62kg`, `69kg`, `77kg`, `85kg`, `94kg`, `105kg`, `105kg+` (men)
- `48kg`, `53kg`, `58kg`, `63kg`, `69kg`, `75kg`, `90kg`, `90kg+` (women)

**Common Errors:**

1. **Invalid lift_type**: If using a test database with limited enums, use `Snatch` or `Clean` in test messages instead of `Squat`/`Deadlift`.

2. **Invalid weight_class**: The default weight class in `upload_routes.py` is `85kg`. Ensure this exists in your database enum.

### User Registration

The email sender must be a registered user in the Tom's Gym database:
- The system looks up users by email address
- If user not found, the upload fails with "User not found"
- For testing, insert test users directly:
  ```sql
  INSERT INTO users (id, email, name, created_at) 
  VALUES (gen_random_uuid(), 'your-email@gmail.com', 'Test User', NOW());
  ```

### Video Size Limits

- Gmail attachment limit: **25 MB**
- For larger videos, users should compress before sending or use Google Drive links (not yet supported)

### Browser Playback Compatibility

- Some MP4 files use **MPEG-4 Part 2 (`mp4v`)**, which many browsers won't play.
- Prefer **H.264 (AVC) + AAC** for reliable playback in the browser.
- If an upload arrives with `Content-Type: application/octet-stream`, playback may fail even if the codec is valid.
- The backend now infers common video MIME types (e.g., `.mp4` → `video/mp4`) when missing.

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

- [x] Dedicated email address created (`t30gupload@gmail.com`)
- [x] App password configured
- [x] IMAP access enabled
- [x] Environment variables set in docker-compose
- [x] Email processor running (background thread in Flask app)
- [x] Error notification emails working
- [x] Success confirmation emails include video link
- [ ] Monitoring/alerting configured
- [ ] User documentation published
- [ ] Rate limiting configured
- [ ] Logs being collected to persistent storage

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

## Implementation Files

The email upload integration is implemented across the following files:

| File | Purpose |
|------|---------|
| `Backend/toms_gym/integrations/__init__.py` | Package init (empty) |
| `Backend/toms_gym/integrations/email_upload.py` | Main email processing logic, Flask blueprint |
| `Backend/toms_gym/app.py` | Blueprint registration, starts background processor |
| `docker-compose.yml` | Email environment variables for production |
| `docker-compose.override.yml` | Email environment variables for local development |

### Key Functions in `email_upload.py`

| Function | Description |
|----------|-------------|
| `parse_t30g_message()` | Extract weight/lift type from message body |
| `get_video_attachments()` | Find video files in email attachments |
| `upload_video_to_backend()` | Call `/upload` endpoint with video |
| `send_confirmation_email()` | Send success/failure email with video link |
| `check_inbox()` | Main processing loop (IMAP polling) |
| `start_background_processor()` | Starts the background thread |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/integrations/email/health` | GET | Health check with stats |
| `/integrations/email/check` | POST | Manually trigger inbox check |
| `/integrations/email/test` | POST | Test email parsing (dev only) |
| `/integrations/email/stats/reset` | POST | Reset processing counters |

---

## Future Enhancements

1. **SendGrid/Mailgun webhook**: Real-time email processing without polling
2. **Google Drive links**: Handle videos shared as Drive links
3. **Multiple spaces**: Support different email addresses per Chat space
4. **Confirmation in Chat**: If Workspace, post confirmation back to Chat
5. **Edit support**: Allow re-processing if user forwards a correction
6. **Support all lift types**: Add Squat, Deadlift, Bench to database enums for full support
