import { useDroppable } from '@dnd-kit/core'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { QuotationCard } from './quotation-card'
import { Plus } from 'lucide-react'
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
  const { setNodeRef, isOver } = useDroppable({
    id: column.id
  })

  const colorClasses = {
    muted: 'border-slate-200 bg-slate-50',
    warning: 'border-yellow-200 bg-yellow-50',
    primary: 'border-blue-200 bg-blue-50',
    success: 'border-green-200 bg-green-50'
  }

  const badgeVariants = {
    muted: 'secondary',
    warning: 'outline',
    primary: 'default',
    success: 'outline'
  }

  const badgeColors = {
    muted: 'text-slate-600 border-slate-300',
    warning: 'text-yellow-700 border-yellow-300',
    primary: 'text-blue-700 border-blue-300',
    success: 'text-green-700 border-green-300'
  }

  return (
    <Card className={cn(
      'h-fit transition-colors',
      colorClasses[column.color],
      isOver && 'ring-2 ring-primary ring-offset-2'
    )}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2">
            {column.title}
            <Badge 
              variant={badgeVariants[column.color] as any}
              className={cn('text-xs', badgeColors[column.color])}
            >
              {quotations.length}
            </Badge>
          </span>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
            <Plus className="h-3 w-3" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent 
        ref={setNodeRef}
        className="space-y-3 min-h-[400px] pb-4"
      >
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-32 bg-white/50 rounded-lg border-2 border-dashed border-slate-200"></div>
              </div>
            ))}
          </div>
        ) : quotations.length > 0 ? (
          <div className="space-y-3">
            {quotations.map((quotation) => (
              <QuotationCard 
                key={quotation.id} 
                quotation={quotation}
              />
            ))}
          </div>
        ) : (
          <div className="h-32 border-2 border-dashed border-slate-200 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Nenhuma cotação</p>
              <Button variant="ghost" size="sm" className="mt-2">
                <Plus className="h-3 w-3 mr-1" />
                Adicionar
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}