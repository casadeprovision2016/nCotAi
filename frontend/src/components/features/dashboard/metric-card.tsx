import { Card, CardContent } from '@/components/ui/card'
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
    success: 'border-l-green-500 bg-green-50',
    warning: 'border-l-yellow-500 bg-yellow-50',
    destructive: 'border-l-red-500 bg-red-50',
  }

  const iconColorClasses = {
    primary: 'text-primary bg-primary/10',
    success: 'text-green-600 bg-green-100',
    warning: 'text-yellow-600 bg-yellow-100',
    destructive: 'text-red-600 bg-red-100',
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
                trend.isPositive ? 'text-green-600' : 'text-red-600'
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