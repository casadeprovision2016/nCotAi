# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

COTAI (Sistema de Automação para Cotações e Editais) is a full-stack SaaS platform designed to automate the lifecycle of participation in public and private tenders. The system employs AI to streamline edital analysis, quotation management, and competitive scenario simulation.

## Architecture

### Technology Stack
- **Backend**: Python (FastAPI) - Core API and business logic
- **Frontend**: React 18 + TypeScript - Modern SPA with type safety
  - **UI Framework**: Tailwind CSS + Shadcn/UI components
  - **State Management**: TanStack Query (React Query) for server state
  - **Forms**: React Hook Form + Zod validation
  - **Routing**: React Router v6 with protected routes
  - **Icons**: Lucide React icon library
  - **Testing**: Vitest + React Testing Library + Cypress E2E
- **Specialized Services**: Go - High-performance PDF processing
- **Databases**: 
  - PostgreSQL for relational/structured data
  - MongoDB for unstructured data (AI analysis results)
- **Message Queue**: Redis Streams with Celery for async tasks
- **Security**: Service mesh with Linkerd for mTLS, HashiCorp Vault for secrets
- **Observability**: OpenTelemetry, Prometheus, Jaeger

### Core Modules Architecture
The system is organized into distinct modules:

1. **Site Principal (Landing/Marketing)**: Public portal with lead capture and ROI calculator
2. **Autenticação**: Secure user management with MFA, SSO (Gov.br integration), RBAC
3. **Dashboard**: Main workspace with configurable widgets and real-time metrics
4. **nLic (Futuras Licitações)**: Intelligent tender discovery with ML-powered scoring
5. **CotAi (Kanban System)**: End-to-end tender management workflow
6. **Mensagens**: Contextual chat system with thread management
7. **Tarefas**: Eisenhower matrix-based task management

### Key Technical Patterns
- **Microservices Architecture**: Hybrid approach with service mesh communication
- **Event-Driven Design**: Redis Streams for async processing
- **AI Pipeline**: OCR + NLP for document analysis and risk assessment
- **Security Layers**: RBAC, audit trails, encrypted document storage
- **Performance**: Lazy loading, aggressive caching, Web Workers for heavy computations

## Development Phases

### Phase 1: Foundation (4-6 weeks)
- Landing page with lead capture
- Blog and documentation portal
- ROI calculator and case studies

### Phase 2: Authentication & Security (3-4 weeks)
- User management system
- MFA and SSO implementation
- RBAC with granular permissions

### Phase 3: Core Dashboard & Features (8-10 weeks)
- Multi-module dashboard with drag-drop widgets
- Tender discovery with AI scoring
- Kanban workflow system
- Chat and task management

### Phase 4: Scale & Advanced AI (Ongoing)
- Go-based PDF processing optimization
- Enhanced ML models for tender analysis
- Rust security modules for enterprise features

## Key Business Logic

### Tender Scoring Algorithm
The system uses a weighted scoring model for tender relevance:
- Keyword matching (40%)
- Historical success rate with similar agencies (20%)
- Company profile alignment (20%)
- Available timeframe (10%)
- Estimated value vs capacity (10%)

### Workflow States (Kanban)
1. **Cadastro**: Initial tender data entry
2. **Análise**: AI-powered document processing (OCR + NLP)
3. **Cotação**: Price calculation and supplier coordination
4. **Feito**: Finalized proposals with automated reporting

### AI Processing Pipeline
- **OCR**: Tesseract-based text extraction from PDF documents
- **NLP**: spaCy for entity recognition and clause analysis
- **Risk Assessment**: ML models identify problematic clauses
- **Competitive Intelligence**: Historical pricing analysis for optimal bidding

## Security Considerations

- All document processing happens in isolated containers
- Sensitive data encrypted at rest and in transit
- Audit logs for all user actions with immutable trail
- Integration with Gov.br for official authentication
- Role-based access with temporal permissions for consultants

## Performance Requirements

- 99.9% uptime SLA
- Sub-2-second response times for dashboard loads
- Real-time notifications via WebSocket connections
- Offline capability through Service Workers
- Horizontal scaling via Kubernetes orchestration

## Integration Points

- **Gov.br SSO**: Official government authentication
- **WhatsApp Business API**: Critical alert notifications
- **Google Drive/Dropbox**: Document storage integrations
- **Slack/Microsoft Teams**: Workflow notifications
- **External APIs**: Government tender databases

This system is designed to reduce operational time for tender management by 70% while maintaining high security standards and providing intelligent automation for complex business processes.

## Development Commands

### Docker Operations (Recommended for Development)

```bash
# Start all services in development mode
docker-compose up -d

# Start specific services
docker-compose up -d postgres mongodb redis
docker-compose up backend frontend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Rebuild services after changes
docker-compose up -d --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Backend Development (Python FastAPI)

```bash
cd backend

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery workers (in separate terminals)
celery -A app.services.celery worker --loglevel=info
celery -A app.services.celery beat --loglevel=info

# Run specialized worker queues for external integrations
celery -A app.services.celery worker --loglevel=info --queues=notifications,cloud_storage,team_notifications
celery -A app.services.celery worker --loglevel=info --queues=document_processing,analysis

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Initialize database
python scripts/init_db.py

# Code formatting and linting
black .
isort .
flake8
mypy .

# Run tests
pytest
pytest tests/test_specific.py -v
pytest -k "test_function_name"
```

### Frontend Development (React 18 + TypeScript)

```bash
cd frontend

# Install dependencies (use npm consistently)
npm install

# Add new dependencies (always use npm commands)
npm install <package-name>
npm install -D <dev-package-name>

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test
npm run test:coverage
npm run test:watch

# E2E tests
npm run test:e2e
npm run test:e2e:ui

# Linting and formatting
npm run lint
npm run lint:fix
npm run format
npm run format:check

# Type checking
npm run type-check
npm run type-check:watch

# Development tools
npm run storybook        # Component documentation
npm run dev:https        # HTTPS development server
npm run analyze         # Bundle analyzer
```

### Package Management Standards

**IMPORTANT: Always use npm commands for dependency management. Never edit package.json directly.**

```bash
# Installing dependencies
npm install                    # Install all dependencies
npm install <package>         # Add production dependency
npm install -D <package>      # Add development dependency
npm install -g <package>      # Global installation (rare)

# Updating dependencies
npm update                    # Update all dependencies
npm update <package>          # Update specific package
npm outdated                  # Check for outdated packages

# Removing dependencies
npm uninstall <package>       # Remove dependency
npm uninstall -D <package>    # Remove dev dependency

# Dependency analysis
npm list                      # Show dependency tree
npm audit                     # Security audit
npm audit fix                 # Fix security issues

# Cache management
npm cache clean --force       # Clear npm cache
```

### Frontend Project Structure

```
frontend/
├── public/                   # Static assets
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # Shadcn/UI base components
│   │   ├── forms/          # Form components
│   │   ├── layout/         # Layout components
│   │   └── features/       # Feature-specific components
│   ├── pages/              # Page components
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utilities and configurations
│   ├── types/              # TypeScript definitions
│   ├── styles/             # Global styles
│   └── __tests__/          # Test files
├── cypress/                # E2E tests
├── .storybook/            # Storybook configuration
└── dist/                  # Build output
```

### Go PDF Processor Service

```bash
cd services/go-pdf-processor

# Install dependencies
go mod download

# Run development server
go run main.go

# Build binary
go build -o bin/pdf-processor main.go

# Run with specific config
./bin/pdf-processor -config config.yaml

# Run tests
go test ./...
go test -v ./internal/processor
```

### Rust Security Service

```bash
cd services/security-rust

# Install dependencies
cargo build

# Run development server
cargo run

# Run with release optimizations
cargo run --release

# Run tests
cargo test
cargo test --verbose

# Build for production
cargo build --release

# Check code formatting
cargo fmt --check
cargo clippy
```

### External Integrations Management

#### WhatsApp Business API Integration

```bash
# Test WhatsApp connection
curl -X GET "http://localhost:8000/api/whatsapp/health" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Send test message
curl -X POST "http://localhost:8000/api/whatsapp/send/text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"to": "+5511999999999", "message": "Test message from COTAI"}'

# Send tender alert template
curl -X POST "http://localhost:8000/api/whatsapp/send/tender-alert" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"to": "+5511999999999", "tender_data": {"title": "Test Tender", "deadline": "2025-02-15", "estimated_value": "R$ 500.000", "agency": "Test Agency"}}'

# Setup default templates
curl -X POST "http://localhost:8000/api/whatsapp/setup-templates" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Environment Variables for WhatsApp
export WHATSAPP_ACCESS_TOKEN="your_whatsapp_access_token"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
export WHATSAPP_BUSINESS_ACCOUNT_ID="your_business_account_id"
export WHATSAPP_WEBHOOK_VERIFY_TOKEN="your_webhook_verify_token"
```

#### Cloud Storage Integration (Google Drive/Dropbox)

```bash
# List available providers
curl -X GET "http://localhost:8000/api/cloud-storage/providers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Check provider status
curl -X GET "http://localhost:8000/api/cloud-storage/providers/google_drive/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Upload file to cloud storage
curl -X POST "http://localhost:8000/api/cloud-storage/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "provider=google_drive" \
  -F "folder_path=/cotai/documents"

# List files from cloud storage
curl -X GET "http://localhost:8000/api/cloud-storage/files?provider=google_drive&limit=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Sync local folder to cloud
curl -X POST "http://localhost:8000/api/cloud-storage/sync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "google_drive", "local_path": "/app/documents", "remote_path": "/cotai/backup", "sync_direction": "upload"}'

# Environment Variables for Cloud Storage
export GOOGLE_DRIVE_CLIENT_ID="your_google_client_id"
export GOOGLE_DRIVE_CLIENT_SECRET="your_google_client_secret"
export DROPBOX_APP_KEY="your_dropbox_app_key"
export DROPBOX_APP_SECRET="your_dropbox_app_secret"
```

#### Team Notifications Integration (Slack/Teams)

```bash
# List team notification providers
curl -X GET "http://localhost:8000/api/team-notifications/providers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Send message to team channel
curl -X POST "http://localhost:8000/api/team-notifications/send/text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "slack", "channel_id": "C1234567890", "message": "New tender opportunity available!"}'

# Send rich notification with fields
curl -X POST "http://localhost:8000/api/team-notifications/send/rich" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "slack", "channel_id": "C1234567890", "title": "🚨 Tender Alert", "message": "High-value opportunity identified", "color": "#ff6b35", "fields": [{"title": "Value", "value": "R$ 2.5M", "short": true}, {"title": "Deadline", "value": "15 days", "short": true}]}'

# Send workflow notification
curl -X POST "http://localhost:8000/api/team-notifications/send/workflow" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"provider": "teams", "workflow_type": "tender_alert", "channel_id": "19:...", "data": {"tender_title": "Construction Project", "deadline": "2025-02-15", "value": "R$ 1.5M"}}'

# List channels
curl -X GET "http://localhost:8000/api/team-notifications/channels?provider=slack&limit=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Environment Variables for Team Notifications
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
export SLACK_APP_TOKEN="xapp-your-slack-app-token"
export TEAMS_CLIENT_ID="your_teams_client_id"
export TEAMS_CLIENT_SECRET="your_teams_client_secret"
export TEAMS_TENANT_ID="your_teams_tenant_id"
```

#### Celery Tasks for External Integrations

```bash
# Manually trigger cloud storage backup
python -c "
from app.services.tasks.cloud_storage import backup_files_to_cloud
result = backup_files_to_cloud.delay(
    files=[{'path': '/app/documents/file1.pdf', 'name': 'file1.pdf'}],
    provider='google_drive',
    backup_folder='/cotai/backup',
    user_id='user_123'
)
print(f'Task ID: {result.id}')
"

# Manually trigger team notification
python -c "
from app.services.tasks.team_notifications import send_workflow_notification
result = send_workflow_notification.delay(
    workflow_type='tender_alert',
    data={'title': 'Test Tender', 'deadline': '2025-02-15'},
    channels=[{'provider': 'slack', 'channel_id': 'C1234567890'}],
    user_id='user_123'
)
print(f'Task ID: {result.id}')
"

# Check task status
python -c "
from app.services.celery import celery_app
result = celery_app.AsyncResult('TASK_ID_HERE')
print(f'Status: {result.status}')
print(f'Result: {result.result}')
"

# Monitor Celery queues
celery -A app.services.celery inspect active_queues
celery -A app.services.celery inspect stats
celery -A app.services.celery monitor
```

#### Integration Health Monitoring

```bash
# Check all integration health
curl -X GET "http://localhost:8000/api/whatsapp/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"
curl -X GET "http://localhost:8000/api/cloud-storage/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"
curl -X GET "http://localhost:8000/api/team-notifications/health" -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get usage statistics
curl -X GET "http://localhost:8000/api/cloud-storage/usage?days=30" -H "Authorization: Bearer YOUR_JWT_TOKEN"
curl -X GET "http://localhost:8000/api/team-notifications/usage?provider=slack&days=7" -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Test integration connectivity
python scripts/test_integrations.py --all
python scripts/test_integrations.py --whatsapp
python scripts/test_integrations.py --cloud-storage --provider google_drive
python scripts/test_integrations.py --team-notifications --provider slack
```

### Database Operations

```bash
# Connect to PostgreSQL
docker exec -it cotai-postgres psql -U cotai -d cotai

# Connect to MongoDB
docker exec -it cotai-mongodb mongosh -u cotai -p cotai

# Connect to Redis
docker exec -it cotai-redis redis-cli

# Run database initialization scripts
docker exec -it cotai-postgres psql -U cotai -d cotai -f /docker-entrypoint-initdb.d/init.sql
```

### Testing Commands

```bash
# Run all backend tests
cd backend && pytest

# Run frontend tests
cd frontend && npm test

# Run integration tests
pytest tests/integration/

# Run specific test file
pytest tests/test_auth.py -v

# Run tests with coverage
pytest --cov=app tests/
npm test -- --coverage

# Run E2E tests (if configured)
npm run test:e2e
```

## Advanced Architecture Details

### Multi-Service Communication Pattern

The COTAI system employs a hybrid microservices architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React SPA     │    │  Go PDF Proc   │    │ Rust Security   │
│   (Port 3000)   │    │  (Port 8001)   │    │  (Port 8003)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────▶│ FastAPI Backend │◀─────────────┘
                        │  (Port 8000)    │
                        └─────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │ PostgreSQL  │  │   MongoDB   │  │    Redis    │
         │ (Port 5432) │  │ (Port 27017)│  │ (Port 6379) │
         └─────────────┘  └─────────────┘  └─────────────┘
```

### Data Flow Architecture

1. **Structured Data Flow**: User data, tender records, quotations → PostgreSQL
2. **Unstructured Data Flow**: AI analysis results, document processing → MongoDB  
3. **Cache Layer**: Session data, API responses, rate limiting → Redis
4. **Message Queue**: Async tasks, document processing, notifications → Redis Streams + Celery

### External Integration Architecture

The system integrates with multiple external services through a centralized integration pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                 COTAI Core Services                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ WhatsApp    │  │ Cloud       │  │ Team        │        │
│  │ Integration │  │ Storage     │  │ Notifications│       │
│  │ Service     │  │ Manager     │  │ Manager     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                 │                 │             │
└─────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ WhatsApp    │  │Google Drive │  │   Slack     │
    │ Business    │  │   Dropbox   │  │    Teams    │
    │ API         │  │   Storage   │  │Notifications│
    └─────────────┘  └─────────────┘  └─────────────┘
```

### Key Integration Services

**External Integration Services** (`backend/src/services/`):
- **WhatsApp API** (`whatsapp-api/`): Message sending, webhooks, bot automation
- **Cloud Storage** (`cloud-storage/`): Multi-provider file sync (Google Drive, Dropbox)
- **Team Notifications** (`team-notifications/`): Slack/Teams workflow notifications
- **Government APIs** (`government-apis/`): PNCP, COMPRASNET, Receita Federal integration

### AI Processing Pipeline

```
PDF Upload → Go OCR Service → Text Extraction → Python NLP Service → 
Risk Analysis → Competitive Intelligence → MongoDB Storage → 
Real-time Dashboard Updates via WebSocket
```

### Security Architecture

1. **Authentication Flow**: JWT tokens with refresh rotation
2. **Authorization**: RBAC with granular permissions stored in PostgreSQL
3. **Data Protection**: Rust service handles encryption/decryption of sensitive data
4. **Audit Trail**: All actions logged to immutable audit tables
5. **External API Security**: OAuth2 flows for cloud services, webhook validation for messaging

### Async Task Processing

**Celery Task Modules** (`backend/app/services/tasks/`):
- `document_processing.py`: PDF OCR, text extraction, file analysis
- `tender_analysis.py`: AI scoring, risk assessment, competitive analysis
- `notifications.py`: Email, SMS, WhatsApp, Slack/Teams notifications

### Service Health and Monitoring

All services implement health check endpoints:
- FastAPI: `/health`
- Go PDF Processor: `/health`
- Rust Security: `/health`
- External integrations: Built-in connection testing

### Environment Configuration

Key environment variables for service communication:
- `POSTGRES_SERVER`: Database connection
- `MONGODB_URL`: Document storage connection  
- `REDIS_URL`: Cache and message broker
- `CELERY_BROKER_URL`: Task queue connection
- `PDF_PROCESSOR_URL`: Go service endpoint
- `SECURITY_SERVICE_URL`: Rust service endpoint
- External API credentials for WhatsApp, Google Drive, Dropbox, Slack, Teams

### Development Workflow

1. **Local Development**: Use Docker Compose for consistent environment
2. **Service Testing**: Each service has independent test suites
3. **Integration Testing**: Full stack tests via pytest and frontend tests
4. **Code Quality**: Pre-commit hooks for Python (black, isort, flake8), frontend (ESLint, Prettier)
5. **Database Migrations**: Alembic for PostgreSQL schema changes