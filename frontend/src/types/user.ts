export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  role: 'admin' | 'user' | 'viewer'
  department?: string
  phone?: string
  isActive: boolean
  permissions: string[]
  lastLogin?: string
  createdAt: string
  updatedAt: string
}

export interface CreateUserData {
  name: string
  email: string
  role: 'admin' | 'user' | 'viewer'
  department?: string
  phone?: string
  permissions: string[]
}