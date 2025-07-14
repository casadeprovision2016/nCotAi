# Backend Development Commands

FastAPI backend operations for COTAI system.

## Usage
`/backend` - Start development server
`/backend install` - Install dependencies
`/backend migrate` - Run database migrations
`/backend workers` - Start Celery workers
`/backend lint` - Run code formatting and linting
`/backend test` - Run backend tests

## Commands Executed

### Start Development Server
```bash
cd backend
poetry shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Install Dependencies
```bash
cd backend
poetry install
```

### Database Migrations
```bash
cd backend
poetry shell
alembic revision --autogenerate -m "migration description"
alembic upgrade head
python scripts/init_db.py
```

### Start Celery Workers
```bash
cd backend
poetry shell
# Main worker
celery -A app.services.celery worker --loglevel=info

# Specialized workers (run in separate terminals)
celery -A app.services.celery worker --loglevel=info --queues=notifications,cloud_storage,team_notifications
celery -A app.services.celery worker --loglevel=info --queues=document_processing,analysis
celery -A app.services.celery beat --loglevel=info
```

### Code Quality
```bash
cd backend
poetry shell
black .
isort .
flake8
mypy .
```

### Run Tests
```bash
cd backend
poetry shell
pytest
pytest -v
pytest --cov=app tests/
```

## Service URLs
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health