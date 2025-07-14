# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

## Project Overview

COTAI (Sistema de Automação para Cotações e Editais) is a full-stack SaaS platform designed to automate the lifecycle of participation in public and private tenders. The system employs AI to streamline edital analysis, quotation management, and competitive scenario simulation.

The main goal is to reduce operational time for tender management by 70% while maintaining high security standards and providing intelligent automation.

## Current Development Status

The project has completed all four major development phases, including the frontend UI for the main application modules.

*   **Phase 1: Foundation & Web Portal:** ✅ Completed. A professional, responsive landing page with a functional ROI calculator and lead capture forms is implemented.
*   **Phase 2: Authentication & Security:** ✅ Completed. An enterprise-grade security module is in place, featuring MFA, rotating refresh tokens, RBAC, SSO (Gov.br), and a complete audit trail system.
*   **Phase 3: Core Dashboard & Features:** ✅ Completed. The core application is functional, including a real-time notification system, advanced forms, a professional reporting engine, and integration with the PNCP. The main frontend pages (Dashboard, Tenders, Kanban, Messages, Tasks, Reports) are fully implemented.
*   **Phase 4: Scalability & Advanced AI:** ✅ Completed. The architecture has been evolved into high-performance microservices using Go for PDF processing, Rust for security components, and Python for the AI engine. The AI pipeline uses a fine-tuned BERT model for advanced NLP tasks. Observability with OpenTelemetry is fully implemented.

**For a detailed breakdown of all implemented features, please refer to `checkList.md`.**

## Architecture

### Technology Stack
- **Backend**: Python (FastAPI) - Core API and business logic.
- **Frontend**: React (TypeScript) - User interface components.
- **Specialized Services**:
    - Go: High-performance PDF processing and API gateway tasks.
    - Rust: Critical security modules (cryptography, audit).
- **Databases**:
  - PostgreSQL for relational/structured data.
  - MongoDB for unstructured data (AI analysis results).
- **Message Queue**: Redis Streams with Celery for async tasks.
- **Observability**: OpenTelemetry, Prometheus, Jaeger, Grafana.

### Core Modules & Architecture
The system uses a microservices architecture. Key modules include:
1.  **Authentication**: Secure user management with MFA, SSO (Gov.br), RBAC.
2.  **Dashboard**: Main workspace with configurable widgets.
3.  **nLic (Futuras Licitações)**: Intelligent tender discovery with ML-powered scoring.
4.  **CotAi (Kanban System)**: End-to-end tender management workflow.
5.  **Mensagens**: Contextual chat system.
6.  **Tarefas**: Eisenhower matrix-based task management.

## Key Business Logic

### Tender Scoring Algorithm
A weighted scoring model is used for tender relevance:
- Keyword matching (40%)
- Historical success rate with similar agencies (20%)
- Company profile alignment (20%)
- Available timeframe (10%)
- Estimated value vs capacity (10%)

### AI Processing Pipeline
- **OCR**: Tesseract-based text extraction from PDF documents (implemented in Go).
- **NLP**: spaCy and a fine-tuned BERT model for entity recognition, clause analysis, and risk assessment.
- **Competitive Intelligence**: Historical pricing analysis for optimal bidding.

## Integration Points

The system is designed to integrate with several external services:

- **Gov.br SSO**: Official government authentication.
- **Government Tender Databases**:
    - **PNCP (Portal Nacional de Contratações Públicas)**: A key data source. The detailed API documentation is available in `api.md`. The integration service is implemented in `backend/src/services/government-apis/`.
    - **COMPRASNET**: Another government procurement portal.
- **WhatsApp Business API**: For critical alert notifications. The service is implemented in `backend/src/services/whatsapp-api/`.
- **Cloud Storage (Future)**: Google Drive/Dropbox for document storage.
- **Team Notifications (Future)**: Slack/Microsoft Teams for workflow notifications.

## How to Work with this Project

- **Consult Existing Files:** Before making changes, please consult `plano.md` for the project plan, `checkList.md` for the current status, and the existing `*.md` files for architectural and business context.
- **Follow Conventions:** Adhere to the existing code style, structure, and patterns found in the codebase. The project uses a microservices architecture with specific languages for different tasks (Python/FastAPI, Go, Rust, React/TS).
- **API Documentation:** For any work related to the PNCP integration, refer to the detailed manual in `api.md`.
