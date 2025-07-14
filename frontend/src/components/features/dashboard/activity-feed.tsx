import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Activity, 
  FileText, 
  Calculator, 
  User, 
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface ActivityItem {
  id: string
  type: 'tender' | 'quotation' | 'user' | 'system'
  title: string
  description: string
  timestamp: Date
  user?: string
  status?: 'success' | 'warning' | 'info'
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'tender',
    title: 'Nova licitação cadastrada',
    description: 'Licitação "Serviços de TI" foi adicionada ao sistema',
    timestamp: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
    user: 'João Silva',
    status: 'success'
  },
  {
    id: '2',
    type: 'quotation',
    title: 'Cotação atualizada',
    description: 'Cotação #COT-2025-001 movida para "Em análise"',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    user: 'Maria Santos',
    status: 'info'
  },
  {
    id: '3',
    type: 'system',
    title: 'Deadline próximo',
    description: 'Licitação expira em 3 dias',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
    status: 'warning'
  },
  {
    id: '4',
    type: 'quotation',
    title: 'Cotação finalizada',
    description: 'Cotação #COT-2025-002 foi concluída com sucesso',
    timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000), // 8 hours ago
    user: 'Pedro Costa',
    status: 'success'
  },
  {
    id: '5',
    type: 'user',
    title: 'Novo usuário',
    description: 'Ana Lima foi adicionada ao sistema',
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000), // 12 hours ago
    user: 'Admin',
    status: 'info'
  }
]

export function ActivityFeedWidget() {
  const getActivityIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'tender':
        return <FileText className="h-4 w-4" />
      case 'quotation':
        return <Calculator className="h-4 w-4" />
      case 'user':
        return <User className="h-4 w-4" />
      case 'system':
        return <Activity className="h-4 w-4" />
      default:
        return <Activity className="h-4 w-4" />
    }
  }

  const getStatusIcon = (status: ActivityItem['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-3 w-3 text-green-600" />
      case 'warning':
        return <AlertCircle className="h-3 w-3 text-yellow-600" />
      case 'info':
        return <Clock className="h-3 w-3 text-blue-600" />
      default:
        return null
    }
  }

  const getStatusColor = (status: ActivityItem['status']) => {
    switch (status) {
      case 'success':
        return 'border-l-green-500 bg-green-50'
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-50'
      case 'info':
        return 'border-l-blue-500 bg-blue-50'
      default:
        return 'border-l-slate-200 bg-slate-50'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Atividades Recentes
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="space-y-0 max-h-96 overflow-y-auto">
          {mockActivities.map((activity) => (
            <div 
              key={activity.id} 
              className={`p-4 border-l-4 border-b border-slate-100 last:border-b-0 ${getStatusColor(activity.status)}`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 p-2 rounded-lg bg-white border">
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-sm text-foreground">
                      {activity.title}
                    </h4>
                    {getStatusIcon(activity.status)}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {activity.description}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    {activity.user && (
                      <Badge variant="outline" className="text-xs">
                        {activity.user}
                      </Badge>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(activity.timestamp, { 
                        locale: ptBR, 
                        addSuffix: true 
                      })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}