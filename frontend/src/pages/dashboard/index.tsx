import { MetricCard } from '@/components/features/dashboard/metric-card'
import { RecentTendersWidget } from '@/components/features/dashboard/recent-tenders'
import { QuickActionsWidget } from '@/components/features/dashboard/quick-actions'
import { ActivityFeedWidget } from '@/components/features/dashboard/activity-feed'
import { useAuth } from '@/hooks/use-auth'
import { 
  FileText, 
  Calculator, 
  Users, 
  TrendingUp 
} from 'lucide-react'

export function DashboardPage() {
  const { user } = useAuth()

  const metrics = [
    {
      title: 'Licitações Ativas',
      value: 12,
      icon: <FileText className="h-6 w-6" />,
      color: 'primary' as const,
      trend: { value: 12, isPositive: true, period: 'este mês' }
    },
    {
      title: 'Cotações Pendentes',
      value: 5,
      icon: <Calculator className="h-6 w-6" />,
      color: 'warning' as const,
      trend: { value: 5, isPositive: false, period: 'esta semana' }
    },
    {
      title: 'Usuários Ativos',
      value: '24',
      icon: <Users className="h-6 w-6" />,
      color: 'success' as const,
      trend: { value: 8, isPositive: true, period: 'este mês' }
    },
    {
      title: 'Taxa de Conversão',
      value: '68%',
      icon: <TrendingUp className="h-6 w-6" />,
      color: 'success' as const,
      trend: { value: 3, isPositive: true, period: 'este mês' }
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Dashboard
        </h1>
        <p className="text-muted-foreground mt-2">
          Bem-vindo, {user?.name}! Visão geral do sistema COTAI
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((metric, index) => (
          <MetricCard key={index} {...metric} />
        ))}
      </div>

      {/* Widgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentTendersWidget 
            tenders={[]} 
            isLoading={false}
          />
        </div>
        <div className="space-y-6">
          <QuickActionsWidget />
          <ActivityFeedWidget />
        </div>
      </div>
    </div>
  )
}