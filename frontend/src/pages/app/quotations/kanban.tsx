import { useState } from 'react'
import { DndContext, DragOverlay } from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { KanbanColumn } from '@/components/features/quotations/kanban-column'
import { QuotationCard } from '@/components/features/quotations/quotation-card'
import { Plus, Search, Filter, MoreHorizontal } from 'lucide-react'

const columns = [
  { id: 'backlog', title: 'Backlog', color: 'muted' as const },
  { id: 'analysis', title: 'Em Análise', color: 'warning' as const },
  { id: 'ready', title: 'Pronto para Envio', color: 'primary' as const },
  { id: 'completed', title: 'Finalizado', color: 'success' as const }
]

const mockQuotations = [
  {
    id: '1',
    title: 'Cotação para Serviços de Consultoria em TI',
    tender: 'Licitação #LIC-2025-001',
    agency: 'Ministério da Saúde',
    assignee: { id: '1', name: 'João Silva' },
    value: 180000,
    deadline: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
    priority: 'high' as const,
    status: 'backlog'
  },
  {
    id: '2',
    title: 'Orçamento para Equipamentos de Informática',
    tender: 'Licitação #LIC-2025-002',
    agency: 'INSS',
    assignee: { id: '2', name: 'Maria Santos' },
    value: 120000,
    deadline: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
    priority: 'medium' as const,
    status: 'analysis'
  },
  {
    id: '3',
    title: 'Proposta de Desenvolvimento de Sistema Web',
    tender: 'Licitação #LIC-2025-003',
    agency: 'Receita Federal',
    assignee: { id: '3', name: 'Pedro Costa' },
    value: 350000,
    deadline: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000),
    priority: 'high' as const,
    status: 'ready'
  },
  {
    id: '4',
    title: 'Cotação para Licenças de Software',
    tender: 'Licitação #LIC-2025-004',
    agency: 'TCU',
    assignee: { id: '4', name: 'Ana Lima' },
    value: 85000,
    deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    priority: 'low' as const,
    status: 'completed'
  },
  {
    id: '5',
    title: 'Orçamento para Infraestrutura de Rede',
    tender: 'Licitação #LIC-2025-005',
    agency: 'Banco Central',
    assignee: { id: '5', name: 'Carlos Santos' },
    value: 95000,
    deadline: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000),
    priority: 'medium' as const,
    status: 'backlog'
  }
]

export function QuotationsKanbanPage() {
  const [quotations, setQuotations] = useState(mockQuotations)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    search: '',
    assignee: 'all',
    priority: 'all'
  })

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    
    if (!over || active.id === over.id) {
      setActiveId(null)
      return
    }
    
    const quotationId = active.id as string
    const newStatus = over.id as string
    
    setQuotations(prev => 
      prev.map(quotation => 
        quotation.id === quotationId 
          ? { ...quotation, status: newStatus }
          : quotation
      )
    )
    
    setActiveId(null)
  }

  const getQuotationsByStatus = (status: string) => {
    return quotations.filter(q => {
      const matchesStatus = q.status === status
      const matchesSearch = filters.search === '' || 
        q.title.toLowerCase().includes(filters.search.toLowerCase()) ||
        q.tender.toLowerCase().includes(filters.search.toLowerCase())
      const matchesAssignee = filters.assignee === 'all' || q.assignee.id === filters.assignee
      const matchesPriority = filters.priority === 'all' || q.priority === filters.priority
      
      return matchesStatus && matchesSearch && matchesAssignee && matchesPriority
    })
  }

  const getActiveQuotation = () => {
    return quotations.find(q => q.id === activeId)
  }

  const uniqueAssignees = Array.from(
    new Set(quotations.map(q => q.assignee.id))
  ).map(id => {
    const assignee = quotations.find(q => q.assignee.id === id)?.assignee
    return assignee
  }).filter(Boolean)

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
        <div className="flex items-center gap-3">
          <Button variant="outline">
            <MoreHorizontal className="h-4 w-4 mr-2" />
            Mais opções
          </Button>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nova Cotação
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Buscar cotações..." 
              className="pl-10"
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            />
          </div>
        </div>
        
        <Select 
          value={filters.assignee} 
          onValueChange={(value) => setFilters(prev => ({ ...prev, assignee: value }))}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Responsável" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os Responsáveis</SelectItem>
            {uniqueAssignees.map((assignee) => (
              <SelectItem key={assignee?.id} value={assignee?.id || ''}>
                {assignee?.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select 
          value={filters.priority} 
          onValueChange={(value) => setFilters(prev => ({ ...prev, priority: value }))}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Prioridade" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as Prioridades</SelectItem>
            <SelectItem value="high">Alta</SelectItem>
            <SelectItem value="medium">Média</SelectItem>
            <SelectItem value="low">Baixa</SelectItem>
          </SelectContent>
        </Select>

        <Button 
          variant="outline" 
          onClick={() => setFilters({ search: '', assignee: 'all', priority: 'all' })}
        >
          <Filter className="h-4 w-4 mr-2" />
          Limpar
        </Button>
      </div>

      {/* Kanban Board */}
      <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              column={column}
              quotations={getQuotationsByStatus(column.id)}
              isLoading={false}
            />
          ))}
        </div>
        
        <DragOverlay>
          {activeId ? (
            <QuotationCard quotation={getActiveQuotation()!} />
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {columns.map((column) => {
          const count = getQuotationsByStatus(column.id).length
          const totalValue = getQuotationsByStatus(column.id)
            .filter(q => q.value)
            .reduce((sum, q) => sum + (q.value || 0), 0)
          
          return (
            <div key={column.id} className="bg-card p-4 rounded-lg border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{column.title}</p>
                  <p className="text-lg font-semibold">{count} cotações</p>
                  {totalValue > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {totalValue.toLocaleString('pt-BR', {
                        style: 'currency',
                        currency: 'BRL'
                      })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}