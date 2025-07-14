export interface Tender {
  id: string
  title: string
  description: string
  agency: string
  value: number
  deadline: Date
  status: 'active' | 'closed' | 'draft'
  priority: 'high' | 'medium' | 'low'
  category: 'infrastructure' | 'services' | 'goods'
  documents: TenderDocument[]
  createdAt: string
  updatedAt: string
}

export interface TenderDocument {
  id: string
  name: string
  url: string
  type: string
  size: number
  uploadedAt: string
}

export interface TenderFilters {
  search?: string
  status?: string
  category?: string
  dateRange?: {
    from: Date
    to: Date
  } | null
}

export interface CreateTenderData {
  title: string
  description: string
  agency: string
  value: number
  deadline: Date
  category: string
  documents?: File[]
}