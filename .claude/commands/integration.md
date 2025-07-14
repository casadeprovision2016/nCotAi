# External Integrations Commands

Manage and test external service integrations for COTAI.

## Usage
`/integration` - Check all integration health
`/integration whatsapp` - WhatsApp API operations
`/integration cloud` - Cloud storage operations  
`/integration teams` - Team notifications operations
`/integration test` - Test all integrations
`/integration setup` - Setup integration templates

## Commands Executed

### Check All Integration Health
```bash
curl -X GET "http://localhost:8000/api/whatsapp/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"
curl -X GET "http://localhost:8000/api/cloud-storage/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"
curl -X GET "http://localhost:8000/api/team-notifications/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### WhatsApp Operations
```bash
# Test WhatsApp connection
curl -X GET "http://localhost:8000/api/whatsapp/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Send test message
curl -X POST "http://localhost:8000/api/whatsapp/send/text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"to": "+5511999999999", "message": "Test message from COTAI"}'

# Setup templates
curl -X POST "http://localhost:8000/api/whatsapp/setup-templates" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Cloud Storage Operations
```bash
# List providers
curl -X GET "http://localhost:8000/api/cloud-storage/providers" -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Upload file
curl -X POST "http://localhost:8000/api/cloud-storage/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "provider=google_drive"

# Sync folder
curl -X POST "http://localhost:8000/api/cloud-storage/sync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "google_drive", "local_path": "/app/documents", "remote_path": "/cotai/backup"}'
```

### Team Notifications Operations
```bash
# Send team message
curl -X POST "http://localhost:8000/api/team-notifications/send/text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "slack", "channel_id": "C1234567890", "message": "New tender opportunity!"}'

# Send rich notification
curl -X POST "http://localhost:8000/api/team-notifications/send/rich" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "slack", "channel_id": "C1234567890", "title": "🚨 Tender Alert", "message": "High-value opportunity"}'
```

### Test All Integrations
```bash
python scripts/test_integrations.py --all
python scripts/test_integrations.py --whatsapp
python scripts/test_integrations.py --cloud-storage --provider google_drive
python scripts/test_integrations.py --team-notifications --provider slack
```

### Monitor Celery Queues
```bash
celery -A app.services.celery inspect active_queues
celery -A app.services.celery inspect stats
celery -A app.services.celery monitor
```

## Required Environment Variables
```bash
# WhatsApp
export WHATSAPP_ACCESS_TOKEN="your_token"
export WHATSAPP_PHONE_NUMBER_ID="your_id"

# Cloud Storage
export GOOGLE_DRIVE_CLIENT_ID="your_id"
export DROPBOX_APP_KEY="your_key"

# Team Notifications  
export SLACK_BOT_TOKEN="xoxb-your-token"
export TEAMS_CLIENT_ID="your_id"
```