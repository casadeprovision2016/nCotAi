# 🧪 Plano de Testes Frontend - Sistema COTAI

## 📋 Visão Geral

Este documento define o plano de testes abrangente para validar todas as funcionalidades do frontend do sistema COTAI durante e após a implementação.

## 🎯 Objetivos dos Testes

- **Qualidade**: Garantir código robusto e livre de bugs
- **Funcionalidade**: Validar que todas as features funcionam conforme especificado
- **Usabilidade**: Assegurar experiência de usuário intuitiva
- **Performance**: Verificar tempos de resposta e otimização
- **Compatibilidade**: Testar em diferentes browsers e dispositivos
- **Acessibilidade**: Garantir conformidade com WCAG 2.1 Level AA

## 🏗️ Estrutura de Testes

### 1. Testes Unitários (Vitest + React Testing Library)
**Cobertura Mínima**: 85%

#### 1.1 Componentes UI Base
- [ ] **Button Component**
  - Renderização com texto correto
  - Estados: default, loading, disabled
  - Variantes: primary, secondary, destructive, outline, ghost
  - Tamanhos: default, sm, lg, icon
  - Eventos de click
  - Prop `asChild` funcional

- [ ] **Input Component**
  - Renderização correta
  - Tipos de input (text, email, password, etc.)
  - Estados de foco e blur
  - Validação visual de erro
  - Acessibilidade (labels, aria-attributes)

- [ ] **Card Component**
  - Estrutura correta (Header, Content, Footer)
  - Composição de componentes
  - Aplicação de estilos

- [ ] **Badge Component**
  - Variantes de cor e estado
  - Renderização de texto
  - Aplicação de estilos

- [ ] **Checkbox Component**
  - Estados checked/unchecked
  - Eventos de mudança
  - Acessibilidade

#### 1.2 Componentes de Layout
- [ ] **AppLayout**
  - Renderização da estrutura
  - Integração com sidebar e topnav
  - Responsividade

- [ ] **AuthLayout**
  - Renderização para páginas de autenticação
  - Outlet funcionando corretamente

- [ ] **ProtectedRoute**
  - Redirecionamento quando não autenticado
  - Renderização quando autenticado
  - Estados de loading

#### 1.3 Componentes de Formulários
- [ ] **LoginForm**
  - Validação de campos (email, senha)
  - Submissão de formulário
  - Estados de loading
  - Exibição de erros
  - Integração com React Hook Form

#### 1.4 Hooks Customizados
- [ ] **useAuth**
  - Estados: isLoading, isAuthenticated
  - Funções: login, logout, register
  - Integração com React Query
  - Gerenciamento de tokens
  - Tratamento de erros

#### 1.5 Utilitários
- [ ] **cn() function**
  - Combinação de classes CSS
  - Merge de classes com tailwind-merge

- [ ] **Validation schemas (Zod)**
  - loginSchema: validação de email e senha
  - registerSchema: validação completa de registro
  - Mensagens de erro em português

### 2. Testes de Integração
**Foco**: Interação entre componentes e fluxos de dados

#### 2.1 Fluxo de Autenticação
- [ ] **Login completo**
  - Formulário → Hook → API → Redirecionamento
  - Persistência de token
  - Refresh token automático

- [ ] **Logout**
  - Limpeza de estado
  - Redirecionamento para login

- [ ] **Proteção de rotas**
  - Acesso negado sem autenticação
  - Acesso permitido com autenticação válida

#### 2.2 Gerenciamento de Estado
- [ ] **Zustand Stores**
  - AuthStore: setTokens, clearTokens, persistência
  - UIStore: tema, sidebar, estados UI

- [ ] **React Query**
  - Cache de dados
  - Invalidação de queries
  - Estados de loading/error

### 3. Testes End-to-End (Cypress)
**Objetivo**: Validar fluxos completos do usuário

#### 3.1 Fluxo de Autenticação
```javascript
describe('Authentication Flow', () => {
  it('should complete full login flow', () => {
    cy.visit('/auth/login')
    cy.get('[data-testid="email-input"]').type('admin@cotai.com')
    cy.get('[data-testid="password-input"]').type('password123')
    cy.get('[data-testid="login-button"]').click()
    
    cy.url().should('include', '/app')
    cy.get('[data-testid="dashboard-title"]').should('contain', 'Dashboard')
    cy.get('[data-testid="user-name"]').should('contain', 'Admin')
  })

  it('should handle login errors', () => {
    cy.visit('/auth/login')
    cy.get('[data-testid="email-input"]').type('invalid@email.com')
    cy.get('[data-testid="password-input"]').type('wrongpassword')
    cy.get('[data-testid="login-button"]').click()
    
    cy.get('[data-testid="error-message"]').should('be.visible')
    cy.url().should('include', '/auth/login')
  })

  it('should logout successfully', () => {
    cy.login('admin@cotai.com', 'password123')
    cy.visit('/app')
    cy.get('[data-testid="user-menu"]').click()
    cy.get('[data-testid="logout-button"]').click()
    
    cy.url().should('include', '/auth/login')
  })
})
```

#### 3.2 Navegação e Rotas
- [ ] **Roteamento protegido**
  - Redirecionamento automático para login
  - Acesso a rotas após autenticação

- [ ] **Navegação principal**
  - Links da sidebar funcionais
  - Breadcrumbs corretos
  - Histórico de navegação

#### 3.3 Responsividade
- [ ] **Mobile (320px - 768px)**
  - Layout adaptável
  - Menu mobile funcional
  - Formulários utilizáveis

- [ ] **Tablet (768px - 1024px)**
  - Aproveitamento de espaço
  - Navegação intuitiva

- [ ] **Desktop (1024px+)**
  - Layout completo
  - Todas as funcionalidades visíveis

### 4. Testes de Performance
**Ferramentas**: Lighthouse, Web Vitals

#### 4.1 Métricas Core Web Vitals
- [ ] **LCP (Largest Contentful Paint)**: < 2.5s
- [ ] **FID (First Input Delay)**: < 100ms  
- [ ] **CLS (Cumulative Layout Shift)**: < 0.1

#### 4.2 Performance Score
- [ ] **Lighthouse Performance**: > 90
- [ ] **Bundle Size**: < 500KB (gzipped)
- [ ] **Time to Interactive**: < 3s

### 5. Testes de Acessibilidade
**Padrão**: WCAG 2.1 Level AA

#### 5.1 Navegação por Teclado
- [ ] **Tab navigation**
  - Ordem lógica de foco
  - Elementos interativos acessíveis
  - Skip links funcionais

- [ ] **Enter/Space**
  - Ativação de botões
  - Submissão de formulários

#### 5.2 Screen Readers
- [ ] **Semantic HTML**
  - Headers hierárquicos (h1, h2, h3)
  - Labels em formulários
  - Alt text em imagens

- [ ] **ARIA attributes**
  - aria-label, aria-describedby
  - role attributes corretos
  - States (aria-expanded, aria-selected)

#### 5.3 Contraste de Cores
- [ ] **Ratio mínimo**: 4.5:1 para texto normal
- [ ] **Ratio mínimo**: 3:1 para texto grande
- [ ] **Estados de foco**: Visíveis e contrastados

### 6. Testes de Compatibilidade

#### 6.1 Browsers Desktop
- [ ] **Chrome 90+**: Funcionalidade completa
- [ ] **Firefox 85+**: Funcionalidade completa  
- [ ] **Safari 14+**: Funcionalidade completa
- [ ] **Edge 90+**: Funcionalidade completa

#### 6.2 Browsers Mobile
- [ ] **iOS Safari 14+**: Layout e interações
- [ ] **Chrome Mobile 90+**: Performance e usabilidade
- [ ] **Samsung Internet**: Compatibilidade

#### 6.3 Dispositivos
- [ ] **iPhone (375px)**: Layout mobile
- [ ] **iPad (768px)**: Layout tablet
- [ ] **Desktop (1920px)**: Layout completo

## 🚀 Critérios de Aceitação

### Por Funcionalidade

#### Sistema de Autenticação
**✅ Aceito quando:**
- [ ] Login funciona com credenciais válidas
- [ ] Erro exibido para credenciais inválidas
- [ ] Token persistido no localStorage
- [ ] Refresh token funcional
- [ ] Logout limpa estado completamente
- [ ] Rotas protegidas redirecionam corretamente
- [ ] Formulários validam campos obrigatórios
- [ ] Mensagens de erro em português
- [ ] Acessibilidade (navegação por teclado, screen reader)

#### Layout e Navegação  
**✅ Aceito quando:**
- [ ] Sidebar responsiva funcionando
- [ ] Top navigation com user menu
- [ ] Logo e branding corretos
- [ ] Layout adapta a diferentes tamanhos de tela
- [ ] Transições suaves entre páginas
- [ ] Estados de loading apropriados

#### Dashboard
**✅ Aceito quando:**
- [ ] Métricas carregam corretamente
- [ ] Cards responsivos
- [ ] Dados atualizados em tempo real
- [ ] Interações funcionais
- [ ] Performance adequada

## 🛠️ Configuração de Testes

### Scripts de Teste
```json
{
  "scripts": {
    "test": "vitest --config vitest.config.ts",
    "test:coverage": "vitest --config vitest.config.ts --coverage",
    "test:watch": "vitest --config vitest.config.ts --watch",
    "test:e2e": "cypress run",
    "test:e2e:ui": "cypress open",
    "test:all": "npm run test:coverage && npm run test:e2e"
  }
}
```

### Estrutura de Arquivos de Teste
```
src/__tests__/
├── components/
│   ├── ui/
│   │   ├── button.test.tsx
│   │   ├── input.test.tsx
│   │   ├── card.test.tsx
│   │   └── badge.test.tsx
│   ├── forms/
│   │   └── login-form.test.tsx
│   └── layout/
│       ├── app-layout.test.tsx
│       └── protected-route.test.tsx
├── hooks/
│   └── use-auth.test.tsx
├── utils/
│   └── validation.test.ts
└── setup.ts

cypress/e2e/
├── auth.cy.ts
├── navigation.cy.ts
├── dashboard.cy.ts
└── responsive.cy.ts
```

## 📊 Métricas e Relatórios

### Cobertura de Código
- **Mínimo**: 85% linha/branch/função
- **Ideal**: 90%+ para componentes críticos
- **Relatório**: HTML + LCOV para CI/CD

### Relatórios Cypress
- **Screenshots**: Falhas automáticas
- **Vídeos**: Execução completa dos testes
- **Métricas**: Tempo de execução, taxa de sucesso

### Performance Monitoring
- **Bundle Analysis**: Tamanho por chunk
- **Lighthouse CI**: Scores automáticos
- **Web Vitals**: Monitoramento contínuo

## 🔄 Processo de Execução

### Durante Desenvolvimento
1. **TDD**: Escrever testes antes da implementação
2. **Execução contínua**: `npm run test:watch`
3. **Coverage**: Verificar cobertura mínima
4. **E2E críticos**: Rodar testes de fluxo principal

### Before Deploy
1. **Full test suite**: `npm run test:all`
2. **Performance audit**: Lighthouse score
3. **Accessibility check**: axe-core scan
4. **Cross-browser**: Testes em browsers principais

### Post Deploy
1. **Smoke tests**: Fluxos críticos funcionando
2. **Performance monitoring**: Web Vitals em produção
3. **Error tracking**: Sentry/LogRocket integration

## 🎯 Cronograma de Implementação

### Semana 1-2: Testes Unitários Base
- Componentes UI fundamentais
- Hooks básicos
- Utilitários

### Semana 3-4: Testes de Integração
- Fluxos de autenticação
- Gerenciamento de estado
- Rotas protegidas

### Semana 5-6: Testes E2E
- Fluxos críticos do usuário
- Navegação completa
- Responsividade

### Semana 7-8: Performance e Acessibilidade
- Otimização de bundle
- Auditoria de acessibilidade
- Cross-browser testing

## ✅ Checklist Final

Antes do deploy em produção, verificar:

### Funcionalidade
- [ ] Todos os testes unitários passando (85%+ cobertura)
- [ ] Testes E2E críticos passando
- [ ] Fluxos de usuário funcionais

### Performance
- [ ] Lighthouse Score > 90
- [ ] Bundle size < 500KB
- [ ] Core Web Vitals atendidos

### Acessibilidade
- [ ] WCAG 2.1 AA compliance
- [ ] Navegação por teclado
- [ ] Screen reader compatibility

### Compatibilidade
- [ ] Chrome, Firefox, Safari, Edge
- [ ] Mobile responsivo
- [ ] Tablet otimizado

Este plano de testes garante que o frontend do sistema COTAI seja robusto, performático e acessível, atendendo aos mais altos padrões de qualidade para aplicações corporativas.