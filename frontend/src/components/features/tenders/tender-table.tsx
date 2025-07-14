import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  MoreHorizontal, 
  Eye, 
  Edit, 
  Building,
  Calendar,
  DollarSign
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { Tender } from '@/types/tender'

interface TendersDataTableProps {
  data: Tender[]
  isLoading?: boolean
}

const mockTenders: Tender[] = [
  {
    id: '1',
    title: 'Prestação de Serviços de Consultoria em Tecnologia da Informação',
    description: 'Contratação de empresa especializada para prestação de serviços de consultoria em TI',
    agency: 'Ministério da Saúde',
    value: 250000,
    deadline: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000),
    status: 'active',
    priority: 'high',
    category: 'services',
    documents: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: '2',
    title: 'Aquisição de Equipamentos de Informática',
    description: 'Compra de computadores, impressoras e periféricos para modernização do parque tecnológico',
    agency: 'Instituto Nacional do Seguro Social - INSS',
    value: 180000,
    deadline: new Date(Date.now() + 8 * 24 * 60 * 60 * 1000),
    status: 'active',
    priority: 'medium',
    category: 'goods',
    documents: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: '3',
    title: 'Desenvolvimento de Sistema Web para Gestão Tributária',
    description: 'Desenvolvimento de aplicação web para controle e gestão de tributos municipais',
    agency: 'Receita Federal do Brasil',
    value: 500000,
    deadline: new Date(Date.now() + 22 * 24 * 60 * 60 * 1000),
    status: 'draft',
    priority: 'high',
    category: 'services',
    documents: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: '4',
    title: 'Serviços de Manutenção de Infraestrutura de Rede',
    description: 'Contratação de serviços especializados para manutenção preventiva e corretiva da infraestrutura de rede',
    agency: 'Banco Central do Brasil',
    value: 120000,
    deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    status: 'active',
    priority: 'low',
    category: 'infrastructure',
    documents: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  },
  {
    id: '5',
    title: 'Licenciamento de Software de Segurança',
    description: 'Aquisição de licenças de software antivírus e firewall para proteção institucional',
    agency: 'Tribunal de Contas da União - TCU',
    value: 80000,
    deadline: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000),
    status: 'closed',
    priority: 'medium',
    category: 'goods',
    documents: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
]

export function TendersDataTable({ data = mockTenders, isLoading }: TendersDataTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const getStatusBadge = (status: string) => {
    const variants = {
      active: { variant: 'default' as const, label: 'Ativo' },
      closed: { variant: 'secondary' as const, label: 'Fechado' },
      draft: { variant: 'outline' as const, label: 'Rascunho' }
    }
    return variants[status as keyof typeof variants] || variants.active
  }

  const getPriorityBadge = (priority: string) => {
    const variants = {
      high: { variant: 'destructive' as const, label: 'Alta' },
      medium: { variant: 'warning' as const, label: 'Média' },
      low: { variant: 'secondary' as const, label: 'Baixa' }
    }
    return variants[priority as keyof typeof variants] || variants.medium
  }

  const getCategoryLabel = (category: string) => {
    const labels = {
      infrastructure: 'Infraestrutura',
      services: 'Serviços',
      goods: 'Bens'
    }
    return labels[category as keyof typeof labels] || category
  }

  const formatCurrency = (value: number) => {
    return value.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    })
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-16 bg-slate-200 rounded"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentData = data.slice(startIndex, endIndex)
  const totalPages = Math.ceil(data.length / itemsPerPage)

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-0">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 p-4 bg-muted/50 border-b font-medium text-sm">
            <div className="col-span-4">Licitação</div>
            <div className="col-span-2">Órgão</div>
            <div className="col-span-1">Valor</div>
            <div className="col-span-2">Prazo</div>
            <div className="col-span-1">Status</div>
            <div className="col-span-1">Prioridade</div>
            <div className="col-span-1">Ações</div>
          </div>

          {/* Table Body */}
          <div className="divide-y">
            {currentData.map((tender) => {
              const statusBadge = getStatusBadge(tender.status)
              const priorityBadge = getPriorityBadge(tender.priority)

              return (
                <div key={tender.id} className="grid grid-cols-12 gap-4 p-4 hover:bg-muted/30 transition-colors">
                  {/* Tender Info */}
                  <div className="col-span-4">
                    <div className="space-y-1">
                      <h3 className="font-medium text-sm line-clamp-2 leading-tight">
                        {tender.title}
                      </h3>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="outline" className="text-xs px-1.5 py-0.5">
                          {getCategoryLabel(tender.category)}
                        </Badge>
                        <span>ID: {tender.id}</span>
                      </div>
                    </div>
                  </div>

                  {/* Agency */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-2">
                      <Building className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm line-clamp-2">{tender.agency}</span>
                    </div>
                  </div>

                  {/* Value */}
                  <div className="col-span-1">
                    <div className="flex items-center gap-1">
                      <DollarSign className="h-3 w-3 text-muted-foreground" />
                      <span className="text-sm font-medium">
                        {formatCurrency(tender.value)}
                      </span>
                    </div>
                  </div>

                  {/* Deadline */}
                  <div className="col-span-2">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-muted-foreground" />
                      <span className="text-sm">
                        {formatDistanceToNow(tender.deadline, { 
                          locale: ptBR, 
                          addSuffix: true 
                        })}
                      </span>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="col-span-1">
                    <Badge variant={statusBadge.variant} className="text-xs">
                      {statusBadge.label}
                    </Badge>
                  </div>

                  {/* Priority */}
                  <div className="col-span-1">
                    <Badge variant={priorityBadge.variant} className="text-xs">
                      {priorityBadge.label}
                    </Badge>
                  </div>

                  {/* Actions */}
                  <div className="col-span-1">
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Eye className="h-3 w-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Edit className="h-3 w-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <MoreHorizontal className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Mostrando {startIndex + 1} a {Math.min(endIndex, data.length)} de {data.length} licitações
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Anterior
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  className="w-8 h-8 p-0"
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Próximo
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}