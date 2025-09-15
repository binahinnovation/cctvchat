# WhatsApp Integration Setup Guide

## Overview
This guide helps you set up WhatsApp integration for your CCTV Chat application using Twilio WhatsApp API.

## Prerequisites
- Twilio account with WhatsApp enabled
- Python environment with required packages
- ngrok (for local development)

## Environment Variables

Create a `.env` file in your project root with these variables:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890

# App Configuration
APP_BASE_URL=https://your-ngrok-url.ngrok.io
DASHSCOPE_API_KEY=your_dashscope_api_key

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///instance/cctv_chat.db
SECRET_KEY=your_secret_key
```

## Twilio Setup

### 1. Get Twilio Credentials
1. Go to [Twilio Console](https://console.twilio.com/)
2. Copy your Account SID and Auth Token
3. Go to Phone Numbers → Manage → Active numbers
4. Find your WhatsApp-enabled number and copy it

### 2. Configure Webhook (Development)
For local development, use ngrok:

```bash
# Install ngrok
npm install -g ngrok
# or download from https://ngrok.com/

# Start your backend
python backend.py

# In another terminal, expose your backend
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and:
1. Go to Twilio Console → Phone Numbers → Manage → Active numbers
2. Click your WhatsApp number
3. Set webhook URL to: `https://abc123.ngrok.io/twilio/webhook`
4. Set HTTP method to `POST`
5. Save configuration

### 3. Test with Twilio Sandbox (Alternative)
1. Go to [Twilio Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. Follow instructions to join the sandbox
3. Set webhook URL to your ngrok URL + `/twilio/webhook`

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Start the backend:
```bash
python backend.py
```

3. Start the frontend:
```bash
$env:BACKEND_API_URL="http://127.0.0.1:5000/api"
python -m streamlit run -f appnavigation.py
```

## Usage

### 1. Link WhatsApp Account
1. Login to your web dashboard
2. Click "📱 Link WhatsApp" in the sidebar
3. Click "🔗 Generate Link Token"
4. Scan the QR code or click the WhatsApp link
5. Send the 6-digit token to your Twilio WhatsApp number
6. You'll receive a confirmation message

### 2. WhatsApp Commands
Once linked, you can send these commands via WhatsApp:

- **List videos**: `list my videos`
- **Analyze video**: `what happened in [video name]`
- **Analyze video**: `analyze [video name]`
- **Help**: Send any other message to see available commands

### 3. Example Conversations
```
You: list my videos
Bot: 📹 Your recent videos:
• security_cam_2024.mp4 (upload)
• front_door_footage.mp4 (upload)

You: what happened in security_cam_2024.mp4
Bot: 🎥 Analysis of 'security_cam_2024.mp4':
Between 8:00 and 10:00 PM, two people entered the front gate...
```

## Security Features

- **Token-based linking**: 6-digit tokens expire in 10 minutes
- **One-time use**: Tokens can only be used once
- **Signature validation**: All Twilio webhooks are validated
- **User isolation**: Users can only access their own videos

## Troubleshooting

### Common Issues

1. **"Invalid signature" error**
   - Check your `TWILIO_AUTH_TOKEN` is correct
   - Ensure webhook URL is HTTPS (use ngrok for local dev)

2. **"Token invalid or expired"**
   - Tokens expire in 10 minutes
   - Generate a new token from the dashboard

3. **"No linked account found"**
   - Make sure you've completed the linking process
   - Check your WhatsApp number is correctly linked

4. **Video analysis fails**
   - Ensure `DASHSCOPE_API_KEY` is set
   - For uploaded videos, make sure `APP_BASE_URL` is publicly accessible
   - Test with public video URLs first

### Testing Commands

Test the webhook directly:
```bash
curl -X POST https://your-ngrok-url.ngrok.io/twilio/webhook \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+1234567890&Body=123456"
```

## Production Deployment

1. **Use a production Twilio number** (not sandbox)
2. **Set up HTTPS** for your webhook URL
3. **Use environment variables** for all secrets
4. **Monitor webhook logs** for errors
5. **Set up proper database** (PostgreSQL recommended)

## API Endpoints

- `POST /api/whatsapp/link-token` - Generate linking token (authenticated)
- `POST /api/whatsapp/unlink` - Unlink WhatsApp (authenticated)
- `POST /twilio/webhook` - Twilio webhook (public)

## Database Schema

The integration adds these fields to the `users` table:
- `whatsapp_number` (VARCHAR) - Linked WhatsApp number
- `whatsapp_linked_at` (TIMESTAMP) - When linked

And creates a new table:
- `whatsapp_link_tokens` - Stores temporary linking tokens

## Support

For issues:
1. Check the backend logs for errors
2. Verify all environment variables are set
3. Test with Twilio sandbox first
4. Ensure ngrok is running for local development
