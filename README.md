# COTAI - Sistema de Automação para Cotações e Editais

COTAI é uma plataforma SaaS avançada que automatiza o ciclo de vida completo da participação em licitações públicas e privadas, utilizando inteligência artificial para otimizar processos comerciais e administrativos.

## 🚀 Principais Funcionalidades

- **Descoberta Inteligente de Licitações**: Sistema de busca com PLN e scoring de relevância
- **Processamento Automático de Documentos**: OCR e análise de PDFs com IA
- **Gestão de Fluxo Kanban**: Acompanhamento visual do processo licitatório
- **Simulação de Competitividade**: Análise de cenários e precificação inteligente
- **Alertas Proativos**: Notificações personalizadas por múltiplos canais
- **Dashboard Analítico**: KPIs e visualizações interativas em tempo real
- **Colaboração em Equipe**: Chat contextual e gestão de tarefas

## 🏗️ Arquitetura

### Stack Tecnológica

**Backend:**
- Python 3.11+ com FastAPI
- PostgreSQL (dados relacionais)
- MongoDB (dados não estruturados)
- Redis (cache e filas)
- Celery (tarefas assíncronas)

**Frontend:**
- React 18 com TypeScript
- TailwindCSS para styling
- React Query para estado do servidor
- Chart.js para visualizações

**Infraestrutura:**
- Docker e Docker Compose
- Nginx (proxy reverso)
- Service Mesh (Linkerd)
- Observabilidade (OpenTelemetry)

### Estrutura do Projeto

```
cotAi/
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── api/           # Endpoints da API
│   │   ├── core/          # Configuração e segurança
│   │   ├── db/            # Conexões de banco
│   │   ├── models/        # Modelos SQLAlchemy
│   │   ├── schemas/       # Schemas Pydantic
│   │   ├── services/      # Lógica de negócio e Celery
│   │   └── utils/         # Utilitários
│   ├── tests/             # Testes automatizados
│   └── alembic/           # Migrações de banco
├── frontend/              # App React
│   ├── src/
│   │   ├── components/    # Componentes React
│   │   ├── pages/         # Páginas da aplicação
│   │   ├── hooks/         # Hooks customizados
│   │   ├── services/      # Chamadas de API
│   │   ├── types/         # Definições TypeScript
│   │   └── utils/         # Funções utilitárias
│   └── public/            # Arquivos estáticos
├── docs/                  # Documentação
├── scripts/               # Scripts de setup e deploy
└── docker-compose.yml     # Orquestração de containers
```

## 🛠️ Setup de Desenvolvimento

### Pré-requisitos

- Docker e Docker Compose
- Node.js 18+ (para desenvolvimento frontend)
- Python 3.11+ (para desenvolvimento backend)
- Poetry (gerenciamento de dependências Python)

### Instalação Rápida

1. **Clone o repositório:**
   ```bash
   git clone <repository-url>
   cd cotAi
   ```

2. **Configure as variáveis de ambiente:**
   ```bash
   cp backend/.env.example backend/.env
   # Edite o arquivo .env conforme necessário
   ```

3. **Inicie os serviços com Docker:**
   ```bash
   docker-compose up -d
   ```

4. **Acesse a aplicação:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Documentação da API: http://localhost:8000/docs

### Desenvolvimento Local

**Backend:**
```bash
cd backend
poetry install
poetry shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

**Workers Celery:**
```bash
cd backend
celery -A app.services.celery worker --loglevel=info
celery -A app.services.celery beat --loglevel=info
```

## 📊 Funcionalidades por Módulo

### 1. Autenticação e Segurança
- JWT com tokens de acesso e refresh
- RBAC (controle de acesso baseado em função)
- MFA opcional e integração Gov.br
- Auditoria completa de ações

### 2. Dashboard Principal
- KPIs em tempo real
- Gráficos interativos (Donut, Heatmap, Timeline)
- Widgets customizáveis com drag-and-drop
- Modo escuro/claro automático

### 3. nLic (Descoberta de Licitações)
- Busca inteligente com PLN
- Filtros avançados e busca geolocalizada
- Sistema de scoring ponderado (40% keywords, 20% histórico, etc.)
- Alertas automáticos personalizáveis

### 4. CotAi (Gestão Kanban)
- Fluxo de 8 colunas (Backlog → Finalizado)
- Processamento OCR de PDFs
- Análise de risco com IA
- Simulação de cenários de cotação

### 5. Mensagens Colaborativas
- Threads contextuais por edital/tarefa
- Editor rico com anexos
- Notificações em tempo real
- Templates de mensagens

### 6. Gestão de Tarefas
- Matriz de Eisenhower interativa
- Dependências entre tarefas
- Timer Pomodoro integrado
- Balanceamento automático de carga

## 🧪 Testes

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test

# E2E
npm run test:e2e
```

## 📦 Deploy

### Produção com Docker

```bash
# Build das imagens
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Variáveis de Ambiente Principais

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta JWT | `your-secret-key` |
| `POSTGRES_*` | Configurações PostgreSQL | `localhost:5432` |
| `MONGODB_URL` | URL MongoDB | `mongodb://localhost:27017` |
| `REDIS_URL` | URL Redis | `redis://localhost:6379` |
| `SMTP_*` | Configurações de email | - |

## 🔒 Segurança

- Autenticação JWT com rotação de tokens
- Criptografia de dados sensíveis
- Rate limiting por endpoint
- Validação de entrada com Pydantic
- Logs de auditoria imutáveis
- Conformidade LGPD/GDPR

## 📈 Monitoramento

- Health checks para todos os serviços
- Métricas Prometheus
- Tracing distribuído com Jaeger
- Logs centralizados
- Alertas de performance

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

- **Documentação**: [docs/](./docs/)
- **Issues**: GitHub Issues
- **Email**: support@cotai.com

## 🎯 Roadmap

- [ ] Integração com APIs governamentais
- [ ] Módulos de IA avançada
- [ ] App mobile (React Native)
- [ ] Marketplace de fornecedores
- [ ] Análise preditiva de mercado
- [ ] Integração com ERPs corporativos

---

**COTAI** - Transformando a gestão de licitações com inteligência artificial.