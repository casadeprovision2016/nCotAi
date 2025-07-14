import { Outlet, NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/use-auth'
import { cn } from '@/lib/utils'
import { 
  LayoutDashboard, 
  FileText, 
  Calculator, 
  Users, 
  MessageSquare,
  CheckSquare,
  BarChart3,
  Settings,
  LogOut, 
  Bell,
  Search
} from 'lucide-react'

interface NavItemProps {
  icon: React.ReactNode
  label: string
  href: string
  badge?: string | number
}

function NavItem({ icon, label, href, badge }: NavItemProps) {
  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-slate-700 hover:bg-slate-100"
        )
      }
    >
      {icon}
      <span className="flex-1">{label}</span>
      {badge && (
        <Badge variant="secondary" className="h-5 px-1.5 text-xs">
          {badge}
        </Badge>
      )}
    </NavLink>
  )
}

export function AppLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-slate-200 z-50">
        {/* Logo Header */}
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <img src="/logo-cotai.svg" alt="COTAI" className="h-8" />
            <span className="font-bold text-lg">COTAI</span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="p-4 space-y-2">
          <NavItem 
            icon={<LayoutDashboard className="h-4 w-4" />}
            label="Dashboard"
            href="/app"
          />
          <NavItem 
            icon={<FileText className="h-4 w-4" />}
            label="Licitações"
            href="/app/tenders"
            badge="12"
          />
          <NavItem 
            icon={<Calculator className="h-4 w-4" />}
            label="Cotações"
            href="/app/quotations"
            badge="5"
          />
          <NavItem 
            icon={<Users className="h-4 w-4" />}
            label="Usuários"
            href="/app/users"
          />
          <NavItem 
            icon={<MessageSquare className="h-4 w-4" />}
            label="Mensagens"
            href="/app/messages"
            badge="3"
          />
          <NavItem 
            icon={<CheckSquare className="h-4 w-4" />}
            label="Tarefas"
            href="/app/tasks"
          />
          <NavItem 
            icon={<BarChart3 className="h-4 w-4" />}
            label="Relatórios"
            href="/app/reports"
          />
          <NavItem 
            icon={<Settings className="h-4 w-4" />}
            label="Configurações"
            href="/app/settings"
          />
        </nav>
      </div>

      {/* Main Content */}
      <div className="ml-64">
        {/* Top Navigation */}
        <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Search */}
              <div className="flex-1 max-w-lg">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <input 
                    placeholder="Buscar licitações, cotações..." 
                    className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                  />
                </div>
              </div>

              {/* Right Actions */}
              <div className="flex items-center gap-4">
                {/* Notifications */}
                <Button variant="ghost" size="icon" className="relative">
                  <Bell className="h-5 w-5" />
                  <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 text-xs flex items-center justify-center">
                    3
                  </Badge>
                </Button>

                {/* User Info */}
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                  <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-sm font-medium">
                    {user?.name?.charAt(0) || 'U'}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => logout()}>
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}