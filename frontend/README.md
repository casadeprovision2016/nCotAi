# 🚀 COTAI Frontend

Sistema de Automação para Cotações e Editais - Interface Frontend

## 📋 Visão Geral

Frontend moderno e responsivo do sistema COTAI, desenvolvido com React 18, TypeScript e Tailwind CSS. O sistema oferece uma interface intuitiva para gerenciar licitações, cotações e processos relacionados.

## 🛠️ Stack Tecnológica

### Core Framework
- **React 18** - Framework principal com concurrent features
- **TypeScript** - Type safety e melhor developer experience
- **Vite** - Build tool moderna e rápida

### UI e Design System
- **Tailwind CSS v4** - Utility-first CSS framework
- **Shadcn/UI** - Componentes acessíveis e customizáveis
- **Lucide React** - Biblioteca de ícones consistente
- **Framer Motion** - Animações fluidas

### Estado e Data Fetching
- **TanStack Query (React Query)** v5 - Server state management
- **Zustand** - Client state management
- **React Hook Form** v7 - Gerenciamento de formulários
- **Zod** - Schema validation

### Roteamento
- **React Router** v6 - Client-side routing com proteção de rotas

### Testing
- **Vitest** - Unit testing framework
- **React Testing Library** - Component testing
- **Cypress** - End-to-end testing
- **MSW** - API mocking

### Code Quality
- **ESLint** - Linting
- **Prettier** - Code formatting
- **Husky** - Git hooks

## 🚀 Quick Start

### Pré-requisitos
- Node.js 18+
- npm 8+

### Instalação
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser at http://localhost:3000
```

### Variáveis de Ambiente
```bash
VITE_API_URL=http://localhost:8000/api
```

## 📦 Scripts Disponíveis

### Desenvolvimento
```bash
npm run dev              # Servidor de desenvolvimento
npm run dev:https        # Servidor com HTTPS
npm run build           # Build de produção
npm run preview         # Preview do build
```

### Testes
```bash
npm run test            # Testes unitários
npm run test:coverage   # Testes com cobertura
npm run test:watch      # Testes em modo watch
npm run test:e2e        # Testes end-to-end
npm run test:e2e:ui     # Interface do Cypress
```

### Code Quality
```bash
npm run lint            # ESLint
npm run lint:fix        # ESLint com correção automática
npm run format          # Prettier
npm run format:check    # Verificar formatação
npm run type-check      # TypeScript check
```

## 🏗️ Arquitetura do Projeto

```
src/
├── components/
│   ├── ui/                 # Componentes base (Shadcn/UI)
│   ├── forms/             # Componentes de formulário
│   ├── layout/            # Componentes de layout
│   ├── features/          # Componentes específicos por feature
│   └── common/            # Componentes comuns
├── pages/                 # Páginas da aplicação
├── hooks/                 # Custom hooks
├── lib/                   # Utilities e configurações
├── types/                 # Definições TypeScript
├── stores/                # Zustand stores
├── styles/                # Estilos globais
└── __tests__/             # Testes unitários
```

## 🎨 Design System

### Paleta de Cores
```css
--primary: 217 91% 60%;           /* Azul COTAI */
--success: 142 71% 45%;           /* Verde */
--warning: 38 92% 50%;            /* Amarelo */
--destructive: 0 84% 60%;         /* Vermelho */
```

## 🔐 Autenticação

O sistema implementa autenticação completa com:
- Login/logout
- Proteção de rotas
- Refresh token automático
- Persistência de sessão

## 🧪 Testes

### Executar Testes
```bash
npm run test            # Testes unitários
npm run test:e2e        # Testes E2E
npm run test:coverage   # Com cobertura
```

### Metas de Qualidade
- **Cobertura**: 85%+
- **Performance**: Lighthouse > 90
- **Acessibilidade**: WCAG 2.1 AA

## 📱 Features Implementadas

✅ **Configuração Base**
- Vite + React + TypeScript
- Tailwind CSS + Shadcn/UI
- Estrutura de pastas organizada

✅ **Sistema de Autenticação**
- Página de login funcional
- Validação de formulários
- Integração com API
- Rotas protegidas

✅ **Layout Principal**
- Header responsivo
- Navegação básica
- Dashboard inicial

✅ **Testing Framework**
- Vitest configurado
- React Testing Library
- Cypress E2E
- Testes exemplo funcionais

✅ **Development Tools**
- TypeScript configurado
- ESLint + Prettier
- Scripts de desenvolvimento
- Build otimizado

## 🚀 Próximos Passos

🔄 **Em Desenvolvimento**
- Dashboard completo com widgets
- Página de licitações com filtros
- Sistema Kanban para cotações
- Sidebar com navegação completa

📋 **Roadmap**
- Implementar páginas especializadas
- Adicionar mais componentes UI
- Melhorar sistema de testes
- Otimizações de performance

## 📄 Documentação Adicional

- [TEST_PLAN.md](./TEST_PLAN.md) - Plano de testes detalhado
- [CLAUDE.md](../CLAUDE.md) - Documentação do projeto completo

---

**Status**: 🟢 Funcional - Base completa implementada  
**Versão**: 1.0.0  
**Última atualização**: Janeiro 2025
```
