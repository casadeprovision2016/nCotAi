import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProtectedRoute } from '@/components/common/protected-route'
import { AuthLayout } from '@/components/layout/auth-layout'
import { AppLayout } from '@/components/layout/app-layout'

// Pages
import { LoginPage } from '@/pages/auth/login'
import { DashboardPage } from '@/pages/dashboard'
import { TendersPage } from '@/pages/app/tenders'
import { QuotationsKanbanPage } from '@/pages/app/quotations/kanban'

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
            <Route path="quotations" element={<QuotationsKanbanPage />} />
            
            {/* Placeholder routes */}
            <Route path="users" element={<div className="p-8 text-center text-muted-foreground">Página de Usuários em desenvolvimento</div>} />
            <Route path="messages" element={<div className="p-8 text-center text-muted-foreground">Página de Mensagens em desenvolvimento</div>} />
            <Route path="tasks" element={<div className="p-8 text-center text-muted-foreground">Página de Tarefas em desenvolvimento</div>} />
            <Route path="reports" element={<div className="p-8 text-center text-muted-foreground">Página de Relatórios em desenvolvimento</div>} />
            <Route path="settings" element={<div className="p-8 text-center text-muted-foreground">Página de Configurações em desenvolvimento</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
