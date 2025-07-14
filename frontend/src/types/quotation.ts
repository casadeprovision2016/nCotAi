export interface Quotation {
  id: string
  title: string
  tender: string
  tenderId: string
  assignee: {
    id: string
    name: string
    avatar?: string
  }
  value?: number
  deadline: Date
  priority: 'high' | 'medium' | 'low'
  status: 'backlog' | 'analysis' | 'ready' | 'completed'
  description: string
  items: QuotationItem[]
  createdAt: string
  updatedAt: string
}

export interface QuotationItem {
  id: string
  description: string
  quantity: number
  unitPrice: number
  totalPrice: number
}

export interface QuotationFilters {
  search?: string
  status?: string
  assignee?: string
  priority?: string
}

export interface CreateQuotationData {
  title: string
  tenderId: string
  description: string
  assigneeId: string
  deadline: Date
  priority: 'high' | 'medium' | 'low'
  items: Omit<QuotationItem, 'id'>[]
}

export type QuotationStatus = 'backlog' | 'analysis' | 'ready' | 'completed'