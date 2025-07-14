# COTAI Frontend

React TypeScript frontend para o sistema COTAI.

## Estrutura

```
src/
├── components/         # Componentes reutilizáveis
│   ├── common/         # Componentes base
│   ├── forms/          # Componentes de formulário
│   ├── layout/         # Layout components
│   └── ui/             # UI components
├── pages/              # Páginas da aplicação
│   ├── auth/           # Autenticação
│   ├── dashboard/      # Dashboard
│   ├── tenders/        # Licitações
│   ├── kanban/         # Kanban
│   ├── messages/       # Mensagens
│   └── tasks/          # Tarefas
├── hooks/              # Custom hooks
├── services/           # Serviços de API
├── types/              # Definições TypeScript
├── utils/              # Funções utilitárias
└── styles/             # Estilos globais
```

## Comandos Úteis

```bash
# Instalar dependências
npm install

# Executar em desenvolvimento
npm start

# Build para produção
npm run build

# Executar testes
npm test

# Linting
npm run lint
npm run lint:fix

# Formatação
npm run format
```

## Tecnologias

- **React 18** - Framework frontend
- **TypeScript** - Tipagem estática
- **TailwindCSS** - Framework CSS
- **React Query** - Gerenciamento de estado servidor
- **React Router** - Roteamento
- **React Hook Form** - Formulários
- **Chart.js** - Gráficos
- **Framer Motion** - Animações