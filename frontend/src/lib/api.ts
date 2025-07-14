import axios from 'axios'
import { useAuthStore } from '@/stores/auth-store'
import type { 
  LoginCredentials, 
  RegisterData, 
  AuthResponse,
  TenderFilters, 
  CreateTenderData, 
  Tender,
  QuotationFilters,
  CreateQuotationData,
  Quotation,
  QuotationStatus,
  CreateUserData,
  User
} from '@/types'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
})

// Request interceptor
apiClient.interceptors.request.use((config) => {
  const { token } = useAuthStore.getState()
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  return config
})

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const { refreshToken, clearTokens } = useAuthStore.getState()
      
      if (refreshToken) {
        try {
          const response = await apiClient.post('/auth/refresh', {
            refreshToken
          })
          
          const { accessToken } = response.data
          useAuthStore.getState().setTokens(accessToken, refreshToken)
          
          originalRequest.headers.Authorization = `Bearer ${accessToken}`
          return apiClient(originalRequest)
        } catch (refreshError) {
          clearTokens()
          window.location.href = '/auth/login'
        }
      } else {
        clearTokens()
        window.location.href = '/auth/login'
      }
    }
    
    return Promise.reject(error)
  }
)

export const api = {
  auth: {
    login: (credentials: LoginCredentials): Promise<AuthResponse> =>
      apiClient.post('/auth/login', credentials).then(res => res.data),
    register: (userData: RegisterData): Promise<{ message: string }> =>
      apiClient.post('/auth/register', userData).then(res => res.data),
    logout: (): Promise<{ message: string }> =>
      apiClient.post('/auth/logout').then(res => res.data),
    me: (): Promise<User> =>
      apiClient.get('/auth/me').then(res => res.data),
    refreshToken: (refreshToken: string): Promise<{ accessToken: string }> =>
      apiClient.post('/auth/refresh', { refreshToken }).then(res => res.data),
  },
  tenders: {
    list: (params?: TenderFilters): Promise<Tender[]> =>
      apiClient.get('/tenders', { params }).then(res => res.data),
    create: (data: CreateTenderData): Promise<Tender> =>
      apiClient.post('/tenders', data).then(res => res.data),
    update: (id: string, data: Partial<Tender>): Promise<Tender> =>
      apiClient.put(`/tenders/${id}`, data).then(res => res.data),
    delete: (id: string): Promise<{ message: string }> =>
      apiClient.delete(`/tenders/${id}`).then(res => res.data),
    getById: (id: string): Promise<Tender> =>
      apiClient.get(`/tenders/${id}`).then(res => res.data),
  },
  quotations: {
    list: (params?: QuotationFilters): Promise<Quotation[]> =>
      apiClient.get('/quotations', { params }).then(res => res.data),
    create: (data: CreateQuotationData): Promise<Quotation> =>
      apiClient.post('/quotations', data).then(res => res.data),
    update: (id: string, data: Partial<Quotation>): Promise<Quotation> =>
      apiClient.put(`/quotations/${id}`, data).then(res => res.data),
    updateStatus: (id: string, status: QuotationStatus): Promise<Quotation> =>
      apiClient.patch(`/quotations/${id}/status`, { status }).then(res => res.data),
    delete: (id: string): Promise<{ message: string }> =>
      apiClient.delete(`/quotations/${id}`).then(res => res.data),
  },
  users: {
    list: (): Promise<User[]> =>
      apiClient.get('/users').then(res => res.data),
    create: (data: CreateUserData): Promise<User> =>
      apiClient.post('/users', data).then(res => res.data),
    update: (id: string, data: Partial<User>): Promise<User> =>
      apiClient.put(`/users/${id}`, data).then(res => res.data),
    delete: (id: string): Promise<{ message: string }> =>
      apiClient.delete(`/users/${id}`).then(res => res.data),
  },
}