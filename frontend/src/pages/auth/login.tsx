import { Card, CardContent } from '@/components/ui/card'
import { LoginForm } from '@/components/forms/login-form'

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