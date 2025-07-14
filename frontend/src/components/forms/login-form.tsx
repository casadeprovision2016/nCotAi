import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Mail, Lock, LogIn } from 'lucide-react'
import { Link } from 'react-router-dom'
import { loginSchema } from '@/lib/validations'

type LoginFormData = z.infer<typeof loginSchema>

export function LoginForm() {
  const { login, isLoginLoading } = useAuth()
  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = (data: LoginFormData) => {
    login(data)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium text-slate-700">
          E-mail
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            id="email"
            type="email"
            placeholder="seu@email.com"
            className="pl-10"
            {...register('email')}
          />
        </div>
        {errors.email && (
          <p className="text-sm text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          Senha
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            className="pl-10"
            {...register('password')}
          />
        </div>
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Checkbox id="remember" {...register('remember')} />
          <label htmlFor="remember" className="text-sm text-slate-600">
            Lembrar-me
          </label>
        </div>
        <Link 
          to="/auth/forgot-password" 
          className="text-sm text-primary hover:underline"
        >
          Esqueci minha senha
        </Link>
      </div>

      <Button 
        type="submit" 
        className="w-full" 
        loading={isLoginLoading}
        disabled={isLoginLoading}
      >
        <LogIn className="h-4 w-4 mr-2" />
        Entrar
      </Button>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">ou</span>
        </div>
      </div>

      <Button variant="outline" type="button" className="w-full">
        <img src="/govbr-logo.svg" className="h-4 w-4 mr-2" alt="Gov.br" />
        Entrar com Gov.br
      </Button>

      <div className="text-center text-sm text-slate-600">
        Não tem conta?{' '}
        <Link to="/auth/register" className="text-primary hover:underline">
          Registre-se
        </Link>
      </div>
    </form>
  )
}