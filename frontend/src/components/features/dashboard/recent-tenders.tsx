import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText, Clock, ArrowRight, Building } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface Tender {
  id: string
  title: string
  agency: string
  deadline: Date
  priority: 'high' | 'medium' | 'low'
  status: 'open' | 'closed' | 'draft'
  value: number
}

interface RecentTendersProps {
  tenders: Tender[]
  isLoading?: boolean
}

const mockTenders: Tender[] = [
  {
    id: '1',
    title: 'Prestação de Serviços de Consultoria em TI',
    agency: 'Ministério da Saúde',
    deadline: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000), // 15 days from now
    priority: 'high',
    status: 'open',
    value: 250000
  },
  {
    id: '2',
    title: 'Aquisição de Equipamentos de Informática',
    agency: 'INSS',
    deadline: new Date(Date.now() + 8 * 24 * 60 * 60 * 1000), // 8 days from now
    priority: 'medium',
    status: 'open',
    value: 180000
  },
  {
    id: '3',
    title: 'Desenvolvimento de Sistema Web',
    agency: 'Receita Federal',
    deadline: new Date(Date.now() + 22 * 24 * 60 * 60 * 1000), // 22 days from now
    priority: 'high',
    status: 'open',
    value: 500000
  }
]

export function RecentTendersWidget({ tenders = mockTenders, isLoading }: RecentTendersProps) {
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

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'destructive'
      case 'medium': return 'warning'
      case 'low': return 'secondary'
      default: return 'secondary'
    }
  }

  const formatCurrency = (value: number) => {
    return value.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    })
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
          {tenders.slice(0, 5).map((tender) => (
            <div 
              key={tender.id} 
              className="p-4 border-b border-slate-100 last:border-b-0 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-foreground line-clamp-2 text-sm">
                    {tender.title}
                  </h4>
                  <div className="flex items-center gap-1 mt-1">
                    <Building className="h-3 w-3 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">
                      {tender.agency}
                    </p>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center gap-3">
                      <Badge 
                        variant={getPriorityColor(tender.priority) as any}
                        className="text-xs"
                      >
                        {tender.priority === 'high' ? 'Alta' : 
                         tender.priority === 'medium' ? 'Média' : 'Baixa'}
                      </Badge>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(tender.deadline, { 
                          locale: ptBR, 
                          addSuffix: true 
                        })}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-primary">
                      {formatCurrency(tender.value)}
                    </div>
                  </div>
                </div>
                <Button variant="ghost" size="sm" className="ml-2">
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t">
          <Button variant="outline" className="w-full text-sm">
            Ver todas as licitações
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}