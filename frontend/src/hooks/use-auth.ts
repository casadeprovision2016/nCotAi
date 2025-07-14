import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth-store'
import type { LoginCredentials, RegisterData } from '@/types/auth'

export function useAuth() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { token, setTokens, clearTokens } = useAuthStore()

  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: api.auth.me,
    enabled: !!token,
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: (credentials: LoginCredentials) => api.auth.login(credentials),
    onSuccess: (data) => {
      setTokens(data.accessToken, data.refreshToken)
      queryClient.setQueryData(['auth', 'me'], data.user)
      navigate('/app')
    },
    onError: (error: any) => {
      console.error('Login error:', error.message || 'Credenciais inválidas. Tente novamente.')
    },
  })

  const logoutMutation = useMutation({
    mutationFn: api.auth.logout,
    onSuccess: () => {
      clearTokens()
      queryClient.clear()
      navigate('/auth/login')
    },
  })

  const registerMutation = useMutation({
    mutationFn: (userData: RegisterData) => api.auth.register(userData),
    onSuccess: () => {
      navigate('/auth/login')
    },
    onError: (error: any) => {
      console.error('Register error:', error.message || 'Ocorreu um erro ao registrar.')
    },
  })

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    register: registerMutation.mutate,
    isLoginLoading: loginMutation.isPending,
    isRegisterLoading: registerMutation.isPending,
  }
}