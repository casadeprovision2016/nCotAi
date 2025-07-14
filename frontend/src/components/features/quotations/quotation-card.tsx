import { useDraggable } from '@dnd-kit/core'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { 
  Clock, 
  DollarSign, 
  Building, 
  User,
  MoreHorizontal,
  Eye
} from 'lucide-react'

interface QuotationCardProps {
  quotation: {
    id: string
    title: string
    tender: string
    assignee: {
      id: string
      name: string
      avatar?: string
    }
    value?: number
    deadline: Date
    priority: 'high' | 'medium' | 'low'
    status: string
    agency?: string
  }
}

export function QuotationCard({ quotation }: QuotationCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: quotation.id
  })

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
  } : undefined

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
    <Card 
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`cursor-grab hover:shadow-md transition-shadow ${
        isDragging ? 'opacity-50 rotate-5 shadow-lg' : ''
      }`}
    >
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-sm text-foreground line-clamp-2">
                {quotation.title}
              </h4>
              <div className="flex items-center gap-1 mt-1">
                <Building className="h-3 w-3 text-muted-foreground" />
                <p className="text-xs text-muted-foreground line-clamp-1">
                  {quotation.tender}
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100">
              <MoreHorizontal className="h-3 w-3" />
            </Button>
          </div>

          {/* Agency */}
          {quotation.agency && (
            <div className="text-xs text-muted-foreground">
              {quotation.agency}
            </div>
          )}

          {/* Value */}
          {quotation.value && (
            <div className="flex items-center gap-1">
              <DollarSign className="h-3 w-3 text-green-600" />
              <span className="text-sm font-medium text-green-600">
                {formatCurrency(quotation.value)}
              </span>
            </div>
          )}

          {/* Priority and Assignee */}
          <div className="flex items-center justify-between">
            <Badge 
              variant={getPriorityColor(quotation.priority) as any}
              className="text-xs"
            >
              {quotation.priority === 'high' ? 'Alta' : 
               quotation.priority === 'medium' ? 'Média' : 'Baixa'}
            </Badge>
            
            <div className="flex items-center gap-1">
              <User className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">
                {quotation.assignee.name.split(' ')[0]}
              </span>
            </div>
          </div>

          {/* Deadline */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(quotation.deadline, { 
                locale: ptBR, 
                addSuffix: true 
              })}
            </div>
            
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <Eye className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}