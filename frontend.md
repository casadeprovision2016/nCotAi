# Plano de Desenvolvimento Frontend - Sistema COTAI

## 📋 Visão Geral do Projeto

### Objetivo Principal
Desenvolver a interface frontend completa do sistema COTAI (Sistema de Automação para Cotações e Editais), priorizando:
- **Experiência do usuário** intuitiva e moderna
- **Integração completa** com APIs backend
- **Responsividade** e acessibilidade
- **Arquitetura escalável** e manutenível
- **Performance otimizada** para uso corporativo

### Stack Tecnológica Definitiva

**🚀 Core Framework:**
- **React 18** com TypeScript - Framework principal com type safety
- **Vite** - Build tool moderno e rápido (substituindo Create React App)

**🎨 UI e Design System:**
- **Tailwind CSS** v3.4+ - Utility-first CSS framework
- **Shadcn/UI** - Componentes base acessíveis e customizáveis
- **Lucide React** - Biblioteca de ícones moderna e consistente
- **Framer Motion** - Animações fluidas e performáticas

**⚡ Estado e Data Fetching:**
- **TanStack Query (React Query)** v5 - Server state management
- **Zustand** - Client state management (lightweight)
- **React Hook Form** v7 - Gerenciamento de formulários
- **Zod** - Schema validation e type safety

**🧭 Roteamento e Navegação:**
- **React Router** v6 - Client-side routing
- **React Router DOM** - DOM bindings

**🧪 Testing e Qualidade:**
- **Vitest** - Unit testing framework (Jest alternative)
- **React Testing Library** - Component testing utilities
- **Cypress** - E2E testing framework
- **MSW (Mock Service Worker)** - API mocking

**🔧 Development Tools:**
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **TypeScript** v5 - Type checking
- **Storybook** - Component documentation
- **Husky** - Git hooks

---

## 🎨 Design System Foundation

### Paleta de Cores Semânticas

```css
/* Cores Primárias */
:root {
  --primary: 217 91% 60%;           /* Azul corporativo COTAI */
  --primary-foreground: 0 0% 98%;
  
  /* Cores de Status */
  --success: 142 71% 45%;           /* Verde - sucesso */
  --warning: 38 92% 50%;            /* Amarelo - atenção */
  --destructive: 0 84% 60%;         /* Vermelho - erro */
  --muted: 210 40% 96%;             /* Cinza neutro */
  
  /* Backgrounds */
  --background: 0 0% 100%;          /* Fundo principal */
  --card: 0 0% 100%;                /* Fundo de cards */
  --popover: 0 0% 100%;             /* Fundo de popovers */
  --border: 214 32% 91%;            /* Bordas */
  
  /* Text Colors */
  --foreground: 222 84% 5%;         /* Texto principal */
  --muted-foreground: 215 16% 47%;  /* Texto secundário */
}
```

### Tipografia Hierárquica

```css
/* Heading Scale */
.text-4xl { font-size: 36px; font-weight: 700; } /* h1 - Títulos principais */
.text-3xl { font-size: 30px; font-weight: 600; } /* h2 - Subtítulos */
.text-2xl { font-size: 24px; font-weight: 600; } /* h3 - Seções */
.text-xl  { font-size: 20px; font-weight: 500; } /* h4 - Subseções */

/* Body Scale */
.text-lg   { font-size: 18px; } /* body-lg - Texto destacado */
.text-base { font-size: 16px; } /* body - Texto padrão */
.text-sm   { font-size: 14px; } /* body-sm - Texto pequeno */
.text-xs   { font-size: 12px; } /* caption - Legendas */
```

### Sistema de Espaçamento

```css
/* Grid System */
.container-padding { padding: 24px; }    /* p-6 - Padding de containers */
.section-gap { gap: 24px; }              /* gap-6 - Espaçamento entre seções */
.element-gap { gap: 16px; }              /* gap-4 - Espaçamento entre elementos */
.tight-gap { gap: 8px; }                 /* gap-2 - Espaçamento apertado */

/* Border Radius */
.card-radius { border-radius: 8px; }     /* rounded-lg - Cards */
.button-radius { border-radius: 6px; }   /* rounded-md - Botões */
.input-radius { border-radius: 6px; }    /* rounded-md - Inputs */
```

---

## 🚀 Configuração do Ambiente

### 1. Inicialização do Projeto

```bash
# Criar projeto com Vite + React + TypeScript
npm create vite@latest frontend -- --template react-ts
cd frontend

# Instalar dependências base
npm install

# Configurar Git
git init
git add .
git commit -m "feat: initial commit with Vite + React + TypeScript"
```

### 2. Dependências Principais

```bash
# UI Framework e Styling
npm install tailwindcss postcss autoprefixer
npm install @tailwindcss/forms @tailwindcss/typography
npm install class-variance-authority clsx tailwind-merge

# Shadcn/UI setup
npx shadcn-ui@latest init

# React Router
npm install react-router-dom
npm install -D @types/react-router-dom

# State Management
npm install @tanstack/react-query
npm install zustand

# Forms e Validation
npm install react-hook-form @hookform/resolvers zod

# Icons e Animações
npm install lucide-react framer-motion

# HTTP Client
npm install axios

# Utilities
npm install date-fns react-helmet-async
```

### 3. Dependências de Desenvolvimento

```bash
# Testing
npm install -D vitest @testing-library/react @testing-library/jest-dom
npm install -D @testing-library/user-event jsdom cypress

# API Mocking
npm install -D msw

# Code Quality
npm install -D eslint prettier
npm install -D @typescript-eslint/eslint-plugin @typescript-eslint/parser
npm install -D eslint-plugin-react-hooks eslint-plugin-react-refresh

# Git Hooks
npm install -D husky lint-staged

# Storybook
npm install -D @storybook/react-vite @storybook/addon-essentials

# Bundle Analysis
npm install -D rollup-plugin-visualizer
```

### 4. Scripts do Package.json

```json
{
  "scripts": {
    "dev": "vite",
    "dev:https": "vite --https",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:watch": "vitest --watch",
    "test:e2e": "cypress run",
    "test:e2e:ui": "cypress open",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,js,jsx,json,css,md}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,js,jsx,json,css,md}\"",
    "type-check": "tsc --noEmit",
    "type-check:watch": "tsc --noEmit --watch",
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build",
    "analyze": "npx vite-bundle-analyzer",
    "prepare": "husky install"
  }
}
```

---

## 🏗️ Arquitetura do Projeto

### Estrutura de Pastas Organizada

```
frontend/
├── public/
│   ├── favicon.ico
│   ├── logo-cotai.svg
│   └── govbr-logo.svg
├── src/
│   ├── components/
│   │   ├── ui/                 # Shadcn/UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── select.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── table.tsx
│   │   │   └── index.ts
│   │   ├── forms/              # Form components
│   │   │   ├── login-form.tsx
│   │   │   ├── register-form.tsx
│   │   │   ├── tender-form.tsx
│   │   │   ├── quotation-form.tsx
│   │   │   └── index.ts
│   │   ├── layout/             # Layout components
│   │   │   ├── sidebar.tsx
│   │   │   ├── top-nav.tsx
│   │   │   ├── app-layout.tsx
│   │   │   ├── auth-layout.tsx
│   │   │   └── index.ts
│   │   ├── features/           # Feature-specific components
│   │   │   ├── auth/
│   │   │   │   ├── login-card.tsx
│   │   │   │   ├── mfa-setup.tsx
│   │   │   │   └── govbr-callback.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── metric-card.tsx
│   │   │   │   ├── recent-tenders.tsx
│   │   │   │   ├── quick-actions.tsx
│   │   │   │   └── activity-feed.tsx
│   │   │   ├── tenders/
│   │   │   │   ├── tender-table.tsx
│   │   │   │   ├── tender-filters.tsx
│   │   │   │   └── tender-card.tsx
│   │   │   ├── quotations/
│   │   │   │   ├── kanban-board.tsx
│   │   │   │   ├── kanban-column.tsx
│   │   │   │   └── quotation-card.tsx
│   │   │   └── shared/
│   │   │       ├── data-table.tsx
│   │   │       ├── status-badge.tsx
│   │   │       └── date-picker.tsx
│   │   └── common/             # Common components
│   │       ├── loading-spinner.tsx
│   │       ├── error-boundary.tsx
│   │       ├── protected-route.tsx
│   │       └── breadcrumb.tsx
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── login.tsx
│   │   │   ├── register.tsx
│   │   │   ├── forgot-password.tsx
│   │   │   └── reset-password.tsx
│   │   ├── dashboard/
│   │   │   └── index.tsx
│   │   └── app/
│   │       ├── tenders/
│   │       │   ├── index.tsx
│   │       │   ├── [id].tsx
│   │       │   └── create.tsx
│   │       ├── quotations/
│   │       │   ├── index.tsx
│   │       │   ├── [id].tsx
│   │       │   └── kanban.tsx
│   │       ├── users/
│   │       │   ├── index.tsx
│   │       │   └── [id].tsx
│   │       ├── reports/
│   │       │   └── index.tsx
│   │       └── settings/
│   │           └── index.tsx
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   ├── use-tenders.ts
│   │   ├── use-quotations.ts
│   │   ├── use-users.ts
│   │   ├── use-local-storage.ts
│   │   └── use-debounce.ts
│   ├── lib/
│   │   ├── api.ts              # API client configuration
│   │   ├── auth.ts             # Auth utilities
│   │   ├── utils.ts            # General utilities
│   │   ├── validations.ts      # Zod schemas
│   │   ├── constants.ts        # App constants
│   │   └── query-client.ts     # React Query configuration
│   ├── types/
│   │   ├── auth.ts
│   │   ├── tender.ts
│   │   ├── quotation.ts
│   │   ├── user.ts
│   │   ├── api.ts
│   │   └── index.ts
│   ├── stores/
│   │   ├── auth-store.ts
│   │   ├── ui-store.ts
│   │   └── index.ts
│   ├── styles/
│   │   ├── globals.css
│   │   └── components.css
│   ├── __tests__/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   ├── App.tsx
│   ├── main.tsx
│   └── vite-env.d.ts
├── cypress/
│   ├── e2e/
│   ├── fixtures/
│   └── support/
├── .storybook/
│   ├── main.ts
│   └── preview.ts
├── dist/                       # Build output
├── coverage/                   # Test coverage reports
├── tailwind.config.js
├── vite.config.ts
├── tsconfig.json
├── eslint.config.js
├── prettier.config.js
├── cypress.config.ts
└── package.json
```

---

## 🔧 Configurações Técnicas

### 1. Configuração do Tailwind CSS

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        "scale-in": {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.5s ease-in-out",
        "slide-up": "slide-up 0.3s ease-out",
        "scale-in": "scale-in 0.2s ease-out",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
}
```

### 2. Configuração do Vite

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
          query: ['@tanstack/react-query'],
          forms: ['react-hook-form', 'zod'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
  },
})
```

### 3. Configuração do TypeScript

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

---

## 🚀 Fase 1: Sistema de Autenticação

### 1.1 Estrutura de Páginas de Auth

```
/auth/
├── login/              # Página de login principal
├── register/          # Registro de novos usuários
├── forgot-password/   # Recuperação de senha
├── reset-password/    # Reset com token
├── mfa-setup/         # Configuração 2FA
├── mfa-verify/        # Verificação 2FA
└── govbr-callback/    # Callback Gov.br SSO
```

### 1.2 Layout da Página de Login

```tsx
// pages/auth/login.tsx
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Mail, Lock, LogIn } from 'lucide-react'

export function LoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-6 py-12">
        <div className="max-w-md mx-auto">
          
          {/* Header com Logo */}
          <div className="text-center mb-8">
            <img src="/logo-cotai.svg" alt="COTAI" className="h-12 mx-auto mb-4" />
            <h1 className="text-3xl font-bold text-slate-900">
              Bem-vindo ao COTAI
            </h1>
            <p className="text-slate-600 mt-2">
              Sistema de Automação para Cotações e Editais
            </p>
          </div>

          {/* Card de Login */}
          <Card className="shadow-lg border-0">
            <CardContent className="p-6">
              <LoginForm />
            </CardContent>
          </Card>

          {/* Footer */}
          <div className="text-center mt-6 text-sm text-slate-500">
            © 2025 COTAI. Todos os direitos reservados.
          </div>
        </div>
      </div>
    </div>
  )
}
```

### 1.3 Componente de Formulário de Login

```tsx
// components/forms/login-form.tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Mail, Lock, LogIn } from 'lucide-react'
import { Link } from 'react-router-dom'

const loginSchema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(8, 'Senha deve ter no mínimo 8 caracteres'),
  remember: z.boolean().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

export function LoginForm() {
  const { login, isLoginLoading } = useAuth()
  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = (data: LoginFormData) => {
    login(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium text-slate-700">
          E-mail
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            id="email"
            type="email"
            placeholder="seu@email.com"
            className="pl-10"
            {...register('email')}
          />
        </div>
        {errors.email && (
          <p className="text-sm text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          Senha
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            className="pl-10"
            {...register('password')}
          />
        </div>
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Checkbox id="remember" {...register('remember')} />
          <label htmlFor="remember" className="text-sm text-slate-600">
            Lembrar-me
          </label>
        </div>
        <Link 
          to="/auth/forgot-password" 
          className="text-sm text-primary hover:underline"
        >
          Esqueci minha senha
        </Link>
      </div>

      <Button 
        type="submit" 
        className="w-full" 
        loading={isLoginLoading}
        disabled={isLoginLoading}
      >
        <LogIn className="h-4 w-4 mr-2" />
        Entrar
      </Button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">ou</span>
        </div>
      </div>

      <Button variant="outline" type="button" className="w-full">
        <img src="/govbr-logo.svg" className="h-4 w-4 mr-2" alt="Gov.br" />
        Entrar com Gov.br
      </Button>

      <div className="text-center text-sm text-slate-600">
        Não tem conta?{' '}
        <Link to="/auth/register" className="text-primary hover:underline">
          Registre-se
        </Link>
      </div>
    </form>
  )
}
```

### 1.4 Validações e Esquemas Zod

```typescript
// lib/validations.ts
import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(8, 'Senha deve ter no mínimo 8 caracteres'),
  remember: z.boolean().optional(),
})

export const registerSchema = z.object({
  name: z.string().min(2, 'Nome deve ter no mínimo 2 caracteres'),
  email: z.string().email('E-mail inválido'),
  password: z.string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
    .regex(/[0-9]/, 'Deve conter ao menos um número')
    .regex(/[^A-Za-z0-9]/, 'Deve conter ao menos um caractere especial'),
  confirmPassword: z.string(),
  terms: z.boolean().refine(val => val === true, 'Aceite os termos de uso'),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Senhas não coincidem',
  path: ['confirmPassword'],
})

export const forgotPasswordSchema = z.object({
  email: z.string().email('E-mail inválido'),
})

export const resetPasswordSchema = z.object({
  token: z.string().min(1, 'Token é obrigatório'),
  password: z.string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
    .regex(/[0-9]/, 'Deve conter ao menos um número')
    .regex(/[^A-Za-z0-9]/, 'Deve conter ao menos um caractere especial'),
  confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Senhas não coincidem',
  path: ['confirmPassword'],
})
```

---

## 🏠 Fase 2: Layout Principal da Aplicação

### 2.1 Estrutura de Layout Principal

```tsx
// components/layout/app-layout.tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { TopNav } from './top-nav'

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <Sidebar className="fixed inset-y-0 left-0 w-64 z-50" />

      {/* Main Content */}
      <div className="ml-64">
        {/* Top Navigation */}
        <TopNav className="sticky top-0 z-40 bg-white border-b border-slate-200" />

        {/* Page Content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

### 2.2 Componente Sidebar

```tsx
// components/layout/sidebar.tsx
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { 
  LayoutDashboard, 
  FileText, 
  Calculator, 
  Users, 
  MessageSquare,
  CheckSquare,
  BarChart3,
  Settings
} from 'lucide-react'

interface NavItemProps {
  icon: React.ReactNode
  label: string
  href: string
  badge?: string | number
}

function NavItem({ icon, label, href, badge }: NavItemProps) {
  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-slate-700 hover:bg-slate-100"
        )
      }
    >
      {icon}
      <span className="flex-1">{label}</span>
      {badge && (
        <Badge variant="secondary" className="h-5 px-1.5 text-xs">
          {badge}
        </Badge>
      )}
    </NavLink>
  )
}

export function Sidebar({ className }: { className?: string }) {
  return (
    <div className={cn("bg-white border-r border-slate-200 h-full", className)}>
      {/* Logo Header */}
      <div className="p-6 border-b border-slate-200">
        <img src="/logo-cotai.svg" alt="COTAI" className="h-8" />
      </div>

      {/* Navigation Menu */}
      <nav className="p-4 space-y-2">
        <NavItem 
          icon={<LayoutDashboard className="h-4 w-4" />}
          label="Dashboard"
          href="/app"
        />
        <NavItem 
          icon={<FileText className="h-4 w-4" />}
          label="Licitações"
          href="/app/tenders"
          badge="12"
        />
        <NavItem 
          icon={<Calculator className="h-4 w-4" />}
          label="Cotações"
          href="/app/quotations"
          badge="5"
        />
        <NavItem 
          icon={<Users className="h-4 w-4" />}
          label="Usuários"
          href="/app/users"
        />
        <NavItem 
          icon={<MessageSquare className="h-4 w-4" />}
          label="Mensagens"
          href="/app/messages"
          badge="3"
        />
        <NavItem 
          icon={<CheckSquare className="h-4 w-4" />}
          label="Tarefas"
          href="/app/tasks"
        />
        <NavItem 
          icon={<BarChart3 className="h-4 w-4" />}
          label="Relatórios"
          href="/app/reports"
        />
        <NavItem 
          icon={<Settings className="h-4 w-4" />}
          label="Configurações"
          href="/app/settings"
        />
      </nav>
    </div>
  )
}
```

### 2.3 Componente Top Navigation

```tsx
// components/layout/top-nav.tsx
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Search, Bell, User, LogOut } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'

export function TopNav({ className }: { className?: string }) {
  const { user, logout } = useAuth()

  return (
    <header className={cn("px-6 py-4", className)}>
      <div className="flex items-center justify-between">
        {/* Search */}
        <div className="flex-1 max-w-lg">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="Buscar licitações, cotações..." 
              className="pl-10"
            />
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 text-xs flex items-center justify-center">
              3
            </Badge>
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.avatar} alt={user?.name} />
                  <AvatarFallback>
                    {user?.name?.charAt(0) || 'U'}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <User className="mr-2 h-4 w-4" />
                <span>Perfil</span>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="mr-2 h-4 w-4" />
                <span>Configurações</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Sair</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
```

### 2.4 Configuração de Rotas

```tsx
// App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import { ProtectedRoute } from '@/components/common/protected-route'
import { AuthLayout } from '@/components/layout/auth-layout'
import { AppLayout } from '@/components/layout/app-layout'

// Pages
import { LoginPage } from '@/pages/auth/login'
import { RegisterPage } from '@/pages/auth/register'
import { ForgotPasswordPage } from '@/pages/auth/forgot-password'
import { ResetPasswordPage } from '@/pages/auth/reset-password'
import { DashboardPage } from '@/pages/dashboard'
import { TendersPage } from '@/pages/app/tenders'
import { QuotationsPage } from '@/pages/app/quotations'
import { UsersPage } from '@/pages/app/users'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Navigate to="/auth/login" replace />} />
          
          {/* Auth Routes */}
          <Route path="/auth" element={<AuthLayout />}>
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="forgot-password" element={<ForgotPasswordPage />} />
            <Route path="reset-password" element={<ResetPasswordPage />} />
          </Route>

          {/* Protected App Routes */}
          <Route 
            path="/app" 
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="tenders" element={<TendersPage />} />
            <Route path="quotations" element={<QuotationsPage />} />
            <Route path="users" element={<UsersPage />} />
          </Route>
        </Routes>
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
```

---

## 📊 Fase 3: Dashboard com Widgets

### 3.1 Componente de Métricas

```tsx
// components/features/dashboard/metric-card.tsx
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
    period: string
  }
  color?: 'primary' | 'success' | 'warning' | 'destructive'
}

export function MetricCard({ 
  title, 
  value, 
  icon, 
  trend, 
  color = 'primary' 
}: MetricCardProps) {
  const colorClasses = {
    primary: 'border-l-primary bg-primary/5',
    success: 'border-l-success bg-success/5',
    warning: 'border-l-warning bg-warning/5',
    destructive: 'border-l-destructive bg-destructive/5',
  }

  const iconColorClasses = {
    primary: 'text-primary bg-primary/10',
    success: 'text-success bg-success/10',
    warning: 'text-warning bg-warning/10',
    destructive: 'text-destructive bg-destructive/10',
  }

  return (
    <Card className={cn('border-l-4', colorClasses[color])}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">
              {title}
            </p>
            <p className="text-3xl font-bold text-foreground mt-1">
              {value}
            </p>
            {trend && (
              <div className={cn(
                'flex items-center mt-2 text-sm',
                trend.isPositive ? 'text-success' : 'text-destructive'
              )}>
                {trend.isPositive ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                {Math.abs(trend.value)}% {trend.period}
              </div>
            )}
          </div>
          <div className={cn(
            'p-3 rounded-lg',
            iconColorClasses[color]
          )}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### 3.2 Widget de Licitações Recentes

```tsx
// components/features/dashboard/recent-tenders.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText, Clock, ArrowRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface Tender {
  id: string
  title: string
  agency: string
  deadline: Date
  priority: 'high' | 'medium' | 'low'
  status: 'open' | 'closed' | 'draft'
}

interface RecentTendersProps {
  tenders: Tender[]
  isLoading?: boolean
}

export function RecentTendersWidget({ tenders, isLoading }: RecentTendersProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Licitações Recentes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-slate-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Licitações Recentes
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="space-y-0">
          {tenders.map((tender) => (
            <div 
              key={tender.id} 
              className="p-4 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-medium text-foreground line-clamp-1">
                    {tender.title}
                  </h4>
                  <p className="text-sm text-muted-foreground mt-1">
                    {tender.agency}
                  </p>
                  <div className="flex items-center mt-2 gap-4">
                    <Badge 
                      variant={tender.priority === 'high' ? 'destructive' : 'secondary'}
                    >
                      {tender.priority}
                    </Badge>
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(tender.deadline, { 
                        locale: ptBR, 
                        addSuffix: true 
                      })}
                    </span>
                  </div>
                </div>
                <Button variant="ghost" size="sm">
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
```

### 3.3 Dashboard Principal

```tsx
// pages/dashboard/index.tsx
import { MetricCard } from '@/components/features/dashboard/metric-card'
import { RecentTendersWidget } from '@/components/features/dashboard/recent-tenders'
import { QuickActionsWidget } from '@/components/features/dashboard/quick-actions'
import { ActivityFeedWidget } from '@/components/features/dashboard/activity-feed'
import { useTenders } from '@/hooks/use-tenders'
import { useQuotations } from '@/hooks/use-quotations'
import { 
  FileText, 
  Calculator, 
  Users, 
  TrendingUp 
} from 'lucide-react'

export function DashboardPage() {
  const { data: tenders, isLoading: tendersLoading } = useTenders()
  const { data: quotations, isLoading: quotationsLoading } = useQuotations()

  const metrics = [
    {
      title: 'Licitações Ativas',
      value: tenders?.active || 0,
      icon: <FileText className="h-6 w-6" />,
      color: 'primary' as const,
      trend: { value: 12, isPositive: true, period: 'este mês' }
    },
    {
      title: 'Cotações Pendentes',
      value: quotations?.pending || 0,
      icon: <Calculator className="h-6 w-6" />,
      color: 'warning' as const,
      trend: { value: 5, isPositive: false, period: 'esta semana' }
    },
    {
      title: 'Usuários Ativos',
      value: '24',
      icon: <Users className="h-6 w-6" />,
      color: 'success' as const,
      trend: { value: 8, isPositive: true, period: 'este mês' }
    },
    {
      title: 'Taxa de Conversão',
      value: '68%',
      icon: <TrendingUp className="h-6 w-6" />,
      color: 'success' as const,
      trend: { value: 3, isPositive: true, period: 'este mês' }
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Dashboard
        </h1>
        <p className="text-muted-foreground mt-2">
          Visão geral do sistema COTAI
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric, index) => (
          <MetricCard key={index} {...metric} />
        ))}
      </div>

      {/* Widgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentTendersWidget 
            tenders={tenders?.recent || []} 
            isLoading={tendersLoading}
          />
        </div>
        <div className="space-y-6">
          <QuickActionsWidget />
          <ActivityFeedWidget />
        </div>
      </div>
    </div>
  )
}
```

---

## 🎯 Fase 4: Páginas Especializadas

### 4.1 Página de Licitações

```tsx
// pages/app/tenders/index.tsx
import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TendersDataTable } from '@/components/features/tenders/tender-table'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Plus, Search, Filter } from 'lucide-react'
import { useTenders } from '@/hooks/use-tenders'

export function TendersPage() {
  const [filters, setFilters] = useState({
    search: '',
    status: 'all',
    category: 'all',
    dateRange: null
  })

  const { data: tenders, isLoading } = useTenders(filters)

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Licitações
          </h1>
          <p className="text-muted-foreground mt-2">
            Gerencie todas as licitações do sistema
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Nova Licitação
        </Button>
      </div>

      {/* Filters Bar */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Buscar licitações..." 
                  className="pl-10"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                />
              </div>
            </div>
            
            <Select 
              value={filters.status} 
              onValueChange={(value) => setFilters(prev => ({ ...prev, status: value }))}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="active">Ativo</SelectItem>
                <SelectItem value="draft">Rascunho</SelectItem>
                <SelectItem value="closed">Fechado</SelectItem>
              </SelectContent>
            </Select>

            <Select 
              value={filters.category} 
              onValueChange={(value) => setFilters(prev => ({ ...prev, category: value }))}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Categoria" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="infrastructure">Infraestrutura</SelectItem>
                <SelectItem value="services">Serviços</SelectItem>
                <SelectItem value="goods">Bens</SelectItem>
              </SelectContent>
            </Select>

            <DateRangePicker
              value={filters.dateRange}
              onChange={(dateRange) => setFilters(prev => ({ ...prev, dateRange }))}
            />
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <TendersDataTable 
        data={tenders || []} 
        isLoading={isLoading}
      />
    </div>
  )
}
```

### 4.2 Sistema Kanban de Cotações

```tsx
// pages/app/quotations/kanban.tsx
import { useState } from 'react'
import { DndContext, DragEndEvent } from '@dnd-kit/core'
import { Button } from '@/components/ui/button'
import { KanbanColumn } from '@/components/features/quotations/kanban-column'
import { Plus } from 'lucide-react'
import { useQuotations } from '@/hooks/use-quotations'

const columns = [
  { id: 'backlog', title: 'Backlog', color: 'muted' },
  { id: 'analysis', title: 'Em Análise', color: 'warning' },
  { id: 'ready', title: 'Pronto para Envio', color: 'primary' },
  { id: 'completed', title: 'Finalizado', color: 'success' }
]

export function QuotationsKanbanPage() {
  const { data: quotations, isLoading, updateQuotationStatus } = useQuotations()
  
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    
    if (!over || active.id === over.id) return
    
    const quotationId = active.id as string
    const newStatus = over.id as string
    
    updateQuotationStatus.mutate({ quotationId, status: newStatus })
  }

  const getQuotationsByStatus = (status: string) => {
    return quotations?.filter(q => q.status === status) || []
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Cotações
          </h1>
          <p className="text-muted-foreground mt-2">
            Quadro Kanban para gestão de cotações
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Nova Cotação
        </Button>
      </div>

      {/* Kanban Board */}
      <DndContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              quotations={getQuotationsByStatus(column.id)}
              isLoading={isLoading}
            />
          ))}
        </div>
      </DndContext>
    </div>
  )
}
```

### 4.3 Componente da Coluna Kanban

```tsx
// components/features/quotations/kanban-column.tsx
import { useDroppable } from '@dnd-kit/core'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { QuotationCard } from './quotation-card'
import { cn } from '@/lib/utils'

interface KanbanColumnProps {
  column: {
    id: string
    title: string
    color: 'muted' | 'warning' | 'primary' | 'success'
  }
  quotations: any[]
  isLoading?: boolean
}

export function KanbanColumn({ column, quotations, isLoading }: KanbanColumnProps) {
  const { setNodeRef } = useDroppable({
    id: column.id
  })

  const colorClasses = {
    muted: 'border-muted-foreground/20',
    warning: 'border-warning/20',
    primary: 'border-primary/20',
    success: 'border-success/20'
  }

  const badgeVariants = {
    muted: 'secondary',
    warning: 'warning',
    primary: 'default',
    success: 'success'
  }

  return (
    <Card className={cn('h-fit', colorClasses[column.color])}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span>{column.title}</span>
          <Badge variant={badgeVariants[column.color] as any}>
            {quotations.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent 
        ref={setNodeRef}
        className="space-y-3 min-h-[200px]"
      >
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-muted rounded-lg"></div>
              </div>
            ))}
          </div>
        ) : (
          quotations.map((quotation) => (
            <QuotationCard 
              key={quotation.id} 
              quotation={quotation}
            />
          ))
        )}
      </CardContent>
    </Card>
  )
}
```

### 4.4 Componente do Card de Cotação

```tsx
// components/features/quotations/quotation-card.tsx
import { useDraggable } from '@dnd-kit/core'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Clock, DollarSign } from 'lucide-react'

interface QuotationCardProps {
  quotation: {
    id: string
    title: string
    tender: string
    assignee: {
      name: string
      avatar?: string
    }
    value?: number
    deadline: Date
    priority: 'high' | 'medium' | 'low'
  }
}

export function QuotationCard({ quotation }: QuotationCardProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: quotation.id
  })

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
  } : undefined

  return (
    <Card 
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="cursor-grab hover:shadow-md transition-shadow"
    >
      <CardContent className="p-4">
        <div className="space-y-3">
          <div>
            <h4 className="font-medium text-sm text-foreground line-clamp-2">
              {quotation.title}
            </h4>
            <p className="text-xs text-muted-foreground mt-1">
              {quotation.tender}
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Avatar className="h-6 w-6">
                <AvatarImage src={quotation.assignee.avatar} />
                <AvatarFallback className="text-xs">
                  {quotation.assignee.name.charAt(0)}
                </AvatarFallback>
              </Avatar>
              <Badge 
                variant={quotation.priority === 'high' ? 'destructive' : 'secondary'}
                className="text-xs"
              >
                {quotation.priority}
              </Badge>
            </div>

            {quotation.value && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <DollarSign className="h-3 w-3" />
                {quotation.value.toLocaleString('pt-BR', {
                  style: 'currency',
                  currency: 'BRL'
                })}
              </div>
            )}
          </div>

          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {formatDistanceToNow(quotation.deadline, { 
              locale: ptBR, 
              addSuffix: true 
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## 🔧 Implementação de Hooks e Services

### 5.1 Hook de Autenticação

```typescript
// hooks/use-auth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from '@/components/ui/use-toast'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'
import type { LoginCredentials, User } from '@/types/auth'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { token, setTokens, clearTokens } = useAuthStore()

  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: api.auth.me,
    enabled: !!token,
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: api.auth.login,
    onSuccess: (data) => {
      setTokens(data.accessToken, data.refreshToken)
      queryClient.setQueryData(['auth', 'me'], data.user)
      navigate('/app')
      toast({
        title: "Login realizado com sucesso",
        description: `Bem-vindo, ${data.user.name}!`,
      })
    },
    onError: (error: any) => {
      toast({
        title: "Erro no login",
        description: error.message || "Credenciais inválidas. Tente novamente.",
        variant: "destructive",
      })
    },
  })

  const logoutMutation = useMutation({
    mutationFn: api.auth.logout,
    onSuccess: () => {
      clearTokens()
      queryClient.clear()
      navigate('/auth/login')
      toast({
        title: "Logout realizado com sucesso",
        description: "Você foi desconectado do sistema.",
      })
    },
  })

  const registerMutation = useMutation({
    mutationFn: api.auth.register,
    onSuccess: () => {
      toast({
        title: "Registro realizado com sucesso",
        description: "Você já pode fazer login no sistema.",
      })
      navigate('/auth/login')
    },
    onError: (error: any) => {
      toast({
        title: "Erro no registro",
        description: error.message || "Ocorreu um erro ao registrar.",
        variant: "destructive",
      })
    },
  })

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    register: registerMutation.mutate,
    isLoginLoading: loginMutation.isPending,
    isRegisterLoading: registerMutation.isPending,
  }
}
```

### 5.2 Hook de Licitações

```typescript
// hooks/use-tenders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/components/ui/use-toast'
import { api } from '@/lib/api'
import type { Tender, TenderFilters, CreateTenderData } from '@/types/tender'

export function useTenders(filters?: TenderFilters) {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['tenders', filters],
    queryFn: () => api.tenders.list(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const createTenderMutation = useMutation({
    mutationFn: api.tenders.create,
    onSuccess: (newTender) => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] })
      toast({
        title: "Licitação criada com sucesso",
        description: `A licitação "${newTender.title}" foi criada.`,
      })
    },
    onError: (error: any) => {
      toast({
        title: "Erro ao criar licitação",
        description: error.message || "Ocorreu um erro ao criar a licitação.",
        variant: "destructive",
      })
    },
  })

  const updateTenderMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Tender> }) =>
      api.tenders.update(id, data),
    onSuccess: (updatedTender) => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] })
      toast({
        title: "Licitação atualizada",
        description: `A licitação "${updatedTender.title}" foi atualizada.`,
      })
    },
    onError: (error: any) => {
      toast({
        title: "Erro ao atualizar licitação",
        description: error.message || "Ocorreu um erro ao atualizar a licitação.",
        variant: "destructive",
      })
    },
  })

  const deleteTenderMutation = useMutation({
    mutationFn: api.tenders.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] })
      toast({
        title: "Licitação excluída",
        description: "A licitação foi excluída com sucesso.",
      })
    },
    onError: (error: any) => {
      toast({
        title: "Erro ao excluir licitação",
        description: error.message || "Ocorreu um erro ao excluir a licitação.",
        variant: "destructive",
      })
    },
  })

  return {
    data,
    isLoading,
    error,
    createTender: createTenderMutation.mutate,
    updateTender: updateTenderMutation.mutate,
    deleteTender: deleteTenderMutation.mutate,
    isCreating: createTenderMutation.isPending,
    isUpdating: updateTenderMutation.isPending,
    isDeleting: deleteTenderMutation.isPending,
  }
}
```

### 5.3 API Client

```typescript
// lib/api.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

// Request interceptor
apiClient.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState()
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  return config
})

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const { refreshToken, clearTokens } = useAuthStore.getState()
      
      if (refreshToken) {
        try {
          const response = await apiClient.post('/auth/refresh', {
            refreshToken
          })
          
          const { accessToken } = response.data
          useAuthStore.getState().setTokens(accessToken, refreshToken)
          
          originalRequest.headers.Authorization = `Bearer ${accessToken}`
          return apiClient(originalRequest)
        } catch (refreshError) {
          clearTokens()
          window.location.href = '/auth/login'
        }
      } else {
        clearTokens()
        window.location.href = '/auth/login'
      }
    }
    
    return Promise.reject(error)
  }
)

export const api = {
  auth: {
    login: (credentials: LoginCredentials) =>
      apiClient.post('/auth/login', credentials).then(res => res.data),
    register: (userData: RegisterData) =>
      apiClient.post('/auth/register', userData).then(res => res.data),
    logout: () =>
      apiClient.post('/auth/logout').then(res => res.data),
    me: () =>
      apiClient.get('/auth/me').then(res => res.data),
    refreshToken: (refreshToken: string) =>
      apiClient.post('/auth/refresh', { refreshToken }).then(res => res.data),
  },
  tenders: {
    list: (params?: TenderFilters) =>
      apiClient.get('/tenders', { params }).then(res => res.data),
    create: (data: CreateTenderData) =>
      apiClient.post('/tenders', data).then(res => res.data),
    update: (id: string, data: Partial<Tender>) =>
      apiClient.put(`/tenders/${id}`, data).then(res => res.data),
    delete: (id: string) =>
      apiClient.delete(`/tenders/${id}`).then(res => res.data),
    getById: (id: string) =>
      apiClient.get(`/tenders/${id}`).then(res => res.data),
  },
  quotations: {
    list: (params?: QuotationFilters) =>
      apiClient.get('/quotations', { params }).then(res => res.data),
    create: (data: CreateQuotationData) =>
      apiClient.post('/quotations', data).then(res => res.data),
    update: (id: string, data: Partial<Quotation>) =>
      apiClient.put(`/quotations/${id}`, data).then(res => res.data),
    updateStatus: (id: string, status: QuotationStatus) =>
      apiClient.patch(`/quotations/${id}/status`, { status }).then(res => res.data),
    delete: (id: string) =>
      apiClient.delete(`/quotations/${id}`).then(res => res.data),
  },
  users: {
    list: () =>
      apiClient.get('/users').then(res => res.data),
    create: (data: CreateUserData) =>
      apiClient.post('/users', data).then(res => res.data),
    update: (id: string, data: Partial<User>) =>
      apiClient.put(`/users/${id}`, data).then(res => res.data),
    delete: (id: string) =>
      apiClient.delete(`/users/${id}`).then(res => res.data),
  },
}
```

### 5.4 Stores Zustand

```typescript
// stores/auth-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  refreshToken: string | null
  setTokens: (token: string, refreshToken: string) => void
  clearTokens: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      setTokens: (token, refreshToken) => set({ token, refreshToken }),
      clearTokens: () => set({ token: null, refreshToken: null }),
    }),
    {
      name: 'auth-storage',
    }
  )
)
```

```typescript
// stores/ui-store.ts
import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'light',
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => set({ theme }),
}))
```

---

## 🧪 Testes e Qualidade

### 6.1 Configuração de Testes

```typescript
// src/__tests__/setup.ts
import '@testing-library/jest-dom'
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)

afterEach(() => {
  cleanup()
})

// Mock do router
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/' }),
}))
```

### 6.2 Teste de Componente

```typescript
// src/__tests__/components/button.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
  })

  it('handles click events', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    
    render(<Button onClick={handleClick}>Click me</Button>)
    
    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('shows loading state', () => {
    render(<Button loading>Loading...</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('applies variant styles correctly', () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-destructive')
  })
})
```

### 6.3 Teste de Hook

```typescript
// src/__tests__/hooks/use-auth.test.tsx
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuth } from '@/hooks/use-auth'
import { api } from '@/lib/api'

vi.mock('@/lib/api')

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useAuth', () => {
  it('returns loading state initially', () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    })
    
    expect(result.current.isLoading).toBe(true)
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('handles login successfully', async () => {
    const mockUser = { id: '1', name: 'John Doe', email: 'john@example.com' }
    vi.mocked(api.auth.login).mockResolvedValue({
      user: mockUser,
      accessToken: 'token',
      refreshToken: 'refresh-token',
    })

    const { result } = renderHook(() => useAuth(), {
      wrapper: createWrapper(),
    })

    result.current.login({ email: 'john@example.com', password: 'password' })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })
  })
})
```

### 6.4 Teste E2E com Cypress

```typescript
// cypress/e2e/auth.cy.ts
describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.visit('/auth/login')
  })

  it('should login successfully with valid credentials', () => {
    cy.get('input[type="email"]').type('admin@cotai.com')
    cy.get('input[type="password"]').type('password123')
    cy.get('button[type="submit"]').click()

    cy.url().should('include', '/app')
    cy.get('h1').should('contain', 'Dashboard')
  })

  it('should show error with invalid credentials', () => {
    cy.get('input[type="email"]').type('invalid@email.com')
    cy.get('input[type="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()

    cy.contains('Credenciais inválidas').should('be.visible')
  })

  it('should navigate to register page', () => {
    cy.contains('Registre-se').click()
    cy.url().should('include', '/auth/register')
  })
})
```

---

## 📦 Comandos e Scripts

### Comandos de Desenvolvimento

```bash
# Iniciar servidor de desenvolvimento
npm run dev

# Executar testes
npm run test
npm run test:watch
npm run test:coverage

# Executar testes E2E
npm run test:e2e
npm run test:e2e:ui

# Linting e formatação
npm run lint
npm run lint:fix
npm run format
npm run format:check

# Type checking
npm run type-check
npm run type-check:watch

# Storybook
npm run storybook
npm run build-storybook
```

### Comandos de Build

```bash
# Build de produção
npm run build

# Preview do build
npm run preview

# Análise do bundle
npm run analyze

# Limpeza
rm -rf dist node_modules
npm install
```

---

## 🚀 Deploy e CI/CD

### Configuração do GitHub Actions

```yaml
# .github/workflows/frontend.yml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
    paths: ['frontend/**']
  pull_request:
    branches: [main]
    paths: ['frontend/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Run type checking
        run: npm run type-check
        working-directory: frontend
      
      - name: Run linting
        run: npm run lint
        working-directory: frontend
      
      - name: Run tests
        run: npm run test:coverage
        working-directory: frontend
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: frontend/coverage/lcov.info
          flags: frontend
          name: frontend-coverage

  e2e:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Run E2E tests
        run: npm run test:e2e
        working-directory: frontend

  build:
    runs-on: ubuntu-latest
    needs: [test, e2e]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Build application
        run: npm run build
        working-directory: frontend
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: frontend-build
          path: frontend/dist/
          retention-days: 30

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v3
        with:
          name: frontend-build
          path: dist/
      
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # Add your deployment commands here
```

---

## 📅 Cronograma de Implementação

### Sprint 1 (Semanas 1-2): Fundação e Autenticação
**Objetivos:** Configurar ambiente e implementar sistema de autenticação completo

**Tarefas:**
- ✅ Setup do projeto React + TypeScript + Vite
- ✅ Configuração Tailwind CSS + Shadcn/UI
- ✅ Estruturação de pastas e arquitetura
- ✅ Configuração ESLint, Prettier, Husky
- ✅ Setup React Query + Zustand
- 🔄 Páginas de login, registro, recuperação de senha
- 🔄 Integração com API de autenticação
- 🔄 Validação de formulários com Zod
- 🔄 Testes unitários dos componentes de auth
- 🔄 Configuração de CI/CD básico

**Entregáveis:**
- Sistema de autenticação funcional
- Testes unitários com >80% de cobertura
- Documentação técnica inicial

### Sprint 2 (Semanas 3-4): Layout e Navegação
**Objetivos:** Implementar layout principal e sistema de navegação

**Tarefas:**
- 🔄 Componente de Layout principal responsivo
- 🔄 Sidebar com navegação dinâmica
- 🔄 Top navigation com busca e notificações
- 🔄 Sistema de roteamento protegido
- 🔄 Breadcrumbs e indicadores de navegação
- 🔄 Componentes de loading e error boundary
- 🔄 Tema dark/light (opcional)
- 🔄 Testes de navegação e responsividade

**Entregáveis:**
- Layout principal funcional
- Sistema de navegação completo
- Responsividade para mobile/tablet/desktop

### Sprint 3 (Semanas 5-6): Dashboard e Métricas
**Objetivos:** Desenvolver dashboard com widgets e visualizações

**Tarefas:**
- 🔄 Dashboard principal com métricas
- 🔄 Widgets de licitações recentes
- 🔄 Gráficos e visualizações com Chart.js
- 🔄 Widget de ações rápidas
- 🔄 Feed de atividades recentes
- 🔄 Filtros e período de tempo
- 🔄 Integração com APIs de dados
- 🔄 Otimização de performance

**Entregáveis:**
- Dashboard funcional e interativo
- Widgets responsivos e performáticos
- Integração completa com backend

### Sprint 4 (Semanas 7-8): Páginas Especializadas
**Objetivos:** Implementar páginas de licitações e sistema Kanban

**Tarefas:**
- 🔄 Página de licitações com filtros avançados
- 🔄 Data table com paginação e ordenação
- 🔄 Sistema Kanban de cotações
- 🔄 Drag & drop funcional
- 🔄 Modais de criação/edição
- 🔄 Formulários complexos com validação
- 🔄 Upload de arquivos
- 🔄 Integração completa com APIs CRUD

**Entregáveis:**
- Página de licitações completa
- Sistema Kanban funcional
- Formulários avançados com validação

### Sprint 5 (Semanas 9-10): Qualidade e Deploy
**Objetivos:** Finalizar testes, otimização e deploy

**Tarefas:**
- 🔄 Testes E2E completos com Cypress
- 🔄 Otimização de performance e bundle size
- 🔄 Acessibilidade (WCAG 2.1)
- 🔄 Documentação de componentes com Storybook
- 🔄 Configuração de produção
- 🔄 Deploy automatizado
- 🔄 Monitoramento de erros
- 🔄 Ajustes finais de UX/UI

**Entregáveis:**
- Aplicação 100% testada e otimizada
- Documentação completa
- Deploy em produção
- Monitoramento ativo

---

## 🎯 Metas de Qualidade

### Performance
- **Lighthouse Score:** >90 em todas as métricas
- **First Contentful Paint:** <2s
- **Largest Contentful Paint:** <4s
- **Bundle Size:** <500KB (gzipped)

### Cobertura de Testes
- **Unit Tests:** >85% de cobertura
- **Integration Tests:** Componentes críticos
- **E2E Tests:** Fluxos principais

### Acessibilidade
- **WCAG 2.1 Level AA:** Compliance completo
- **Screen Reader:** Compatibilidade total
- **Keyboard Navigation:** Funcional em todos os elementos

### Compatibilidade
- **Browsers:** Chrome 90+, Firefox 85+, Safari 14+, Edge 90+
- **Mobile:** iOS 14+, Android 10+
- **Responsive:** 320px até 2560px

---

## 📚 Recursos e Documentação

### Documentação Técnica
- **Storybook:** Documentação de componentes
- **TypeDoc:** Documentação de tipos e interfaces
- **README:** Guia de setup e desenvolvimento
- **CHANGELOG:** Histórico de versões

### Recursos de Aprendizado
- **React 18:** [Documentação Oficial](https://react.dev/)
- **TypeScript:** [Handbook](https://www.typescriptlang.org/docs/)
- **Tailwind CSS:** [Documentação](https://tailwindcss.com/docs)
- **React Query:** [TanStack Query](https://tanstack.com/query/latest)
- **Zustand:** [Documentação](https://github.com/pmndrs/zustand)

### Ferramentas de Desenvolvimento
- **VS Code Extensions:**
  - ES7+ React/Redux/React-Native snippets
  - Tailwind CSS IntelliSense
  - TypeScript Importer
  - Auto Rename Tag
  - GitLens

---

## 🔍 Monitoramento e Manutenção

### Métricas de Performance
- **Web Vitals:** Monitoramento contínuo
- **Bundle Analysis:** Análise semanal
- **Lighthouse CI:** Integração no pipeline

### Monitoramento de Erros
- **Sentry:** Captura de erros em produção
- **LogRocket:** Sessões de usuário
- **Analytics:** Comportamento do usuário

### Manutenção
- **Dependências:** Atualização mensal
- **Security Audit:** Auditoria semanal
- **Performance Review:** Análise mensal

---

## 🎉 Considerações Finais

Este plano de desenvolvimento frontend estabelece uma base sólida para o sistema COTAI, priorizando:

1. **Qualidade e Manutenibilidade:** Código bem estruturado e testado
2. **Performance:** Otimização para experiência do usuário
3. **Escalabilidade:** Arquitetura que suporta crescimento
4. **Acessibilidade:** Inclusão para todos os usuários
5. **DevOps:** Integração e deploy contínuos

O resultado será uma aplicação frontend moderna, robusta e fácil de manter, que atende às necessidades específicas do sistema COTAI e pode evoluir com os requisitos futuros.

**Próximos passos:** Iniciar Sprint 1 com setup do ambiente e implementação do sistema de autenticação.