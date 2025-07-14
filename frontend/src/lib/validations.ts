import { z } from 'zod'

export const loginSchema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(8, 'Senha deve ter no mínimo 8 caracteres'),
  remember: z.boolean().optional(),
})

export const registerSchema = z.object({
  name: z.string().min(2, 'Nome deve ter no mínimo 2 caracteres'),
  email: z.string().email('E-mail inválido'),
  password: z.string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
    .regex(/[0-9]/, 'Deve conter ao menos um número')
    .regex(/[^A-Za-z0-9]/, 'Deve conter ao menos um caractere especial'),
  confirmPassword: z.string(),
  terms: z.boolean().refine(val => val === true, 'Aceite os termos de uso'),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Senhas não coincidem',
  path: ['confirmPassword'],
})

export const forgotPasswordSchema = z.object({
  email: z.string().email('E-mail inválido'),
})

export const resetPasswordSchema = z.object({
  token: z.string().min(1, 'Token é obrigatório'),
  password: z.string()
    .min(8, 'Mínimo 8 caracteres')
    .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
    .regex(/[0-9]/, 'Deve conter ao menos um número')
    .regex(/[^A-Za-z0-9]/, 'Deve conter ao menos um caractere especial'),
  confirmPassword: z.string(),
}).refine(data => data.password === data.confirmPassword, {
  message: 'Senhas não coincidem',
  path: ['confirmPassword'],
})

export const tenderSchema = z.object({
  title: z.string().min(5, 'Título deve ter no mínimo 5 caracteres'),
  description: z.string().min(10, 'Descrição deve ter no mínimo 10 caracteres'),
  agency: z.string().min(2, 'Órgão é obrigatório'),
  value: z.number().min(0, 'Valor deve ser maior que zero'),
  deadline: z.date().min(new Date(), 'Data limite deve ser futura'),
  category: z.enum(['infrastructure', 'services', 'goods']),
})

export const quotationSchema = z.object({
  title: z.string().min(5, 'Título deve ter no mínimo 5 caracteres'),
  tenderId: z.string().min(1, 'Licitação é obrigatória'),
  description: z.string().min(10, 'Descrição deve ter no mínimo 10 caracteres'),
  assigneeId: z.string().min(1, 'Responsável é obrigatório'),
  deadline: z.date().min(new Date(), 'Data limite deve ser futura'),
  priority: z.enum(['high', 'medium', 'low']),
  items: z.array(z.object({
    description: z.string().min(1, 'Descrição é obrigatória'),
    quantity: z.number().min(1, 'Quantidade deve ser maior que zero'),
    unitPrice: z.number().min(0, 'Preço unitário deve ser maior que zero'),
  })).min(1, 'Adicione pelo menos um item'),
})

export const userSchema = z.object({
  name: z.string().min(2, 'Nome deve ter no mínimo 2 caracteres'),
  email: z.string().email('E-mail inválido'),
  role: z.enum(['admin', 'user', 'viewer']),
  department: z.string().optional(),
  phone: z.string().optional(),
  permissions: z.array(z.string()),
})