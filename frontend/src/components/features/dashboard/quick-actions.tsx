import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { 
  Plus, 
  FileText, 
  Calculator, 
  Upload, 
  Search,
  Settings
} from 'lucide-react'

interface QuickAction {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  action: () => void
  variant?: 'default' | 'secondary' | 'outline'
}

export function QuickActionsWidget() {
  const quickActions: QuickAction[] = [
    {
      id: 'new-tender',
      title: 'Nova Licitação',
      description: 'Cadastrar uma nova licitação no sistema',
      icon: <FileText className="h-4 w-4" />,
      action: () => console.log('Nova licitação'),
      variant: 'default'
    },
    {
      id: 'new-quotation',
      title: 'Nova Cotação',
      description: 'Criar uma nova cotação',
      icon: <Calculator className="h-4 w-4" />,
      action: () => console.log('Nova cotação'),
      variant: 'secondary'
    },
    {
      id: 'upload-document',
      title: 'Upload de Documentos',
      description: 'Enviar documentos para análise',
      icon: <Upload className="h-4 w-4" />,
      action: () => console.log('Upload documento'),
      variant: 'outline'
    },
    {
      id: 'search-opportunities',
      title: 'Buscar Oportunidades',
      description: 'Encontrar novas licitações',
      icon: <Search className="h-4 w-4" />,
      action: () => console.log('Buscar oportunidades'),
      variant: 'outline'
    }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-5 w-5" />
          Ações Rápidas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {quickActions.map((action) => (
          <Button
            key={action.id}
            variant={action.variant}
            className="w-full justify-start h-auto p-4"
            onClick={action.action}
          >
            <div className="flex items-center gap-3 w-full">
              <div className="flex-shrink-0">
                {action.icon}
              </div>
              <div className="flex-1 text-left">
                <div className="font-medium text-sm">
                  {action.title}
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {action.description}
                </div>
              </div>
            </div>
          </Button>
        ))}
        
        <div className="pt-2 border-t">
          <Button variant="ghost" size="sm" className="w-full">
            <Settings className="h-4 w-4 mr-2" />
            Configurações
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}