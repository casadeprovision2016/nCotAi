# COTAI Backend

FastAPI backend para o sistema COTAI de automação de licitações.

## Estrutura

```
app/
├── api/                 # Endpoints da API
│   ├── endpoints/       # Endpoints específicos
│   └── api.py          # Router principal
├── core/               # Configuração central
│   ├── config.py       # Settings da aplicação
│   └── security.py     # Utilitários de segurança
├── db/                 # Configuração de banco
│   ├── session.py      # SQLAlchemy session
│   ├── mongodb.py      # MongoDB connection
│   └── dependencies.py # Dependency injection
├── models/             # Modelos SQLAlchemy
├── schemas/            # Schemas Pydantic
├── services/           # Lógica de negócio
│   ├── celery.py       # Configuração Celery
│   └── tasks/          # Tarefas assíncronas
└── utils/              # Utilitários
```

## Comandos Úteis

```bash
# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Executar servidor de desenvolvimento
uvicorn app.main:app --reload

# Executar workers Celery
celery -A app.services.celery worker --loglevel=info
celery -A app.services.celery beat --loglevel=info

# Executar testes
pytest

# Gerar migrações
alembic revision --autogenerate -m "description"

# Aplicar migrações
alembic upgrade head

# Linting
black .
isort .
flake8
```