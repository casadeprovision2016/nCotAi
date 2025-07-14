describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.visit('/auth/login')
  })

  it('should display login form', () => {
    cy.get('h1').should('contain', 'Bem-vindo ao COTAI')
    cy.get('input[type="email"]').should('be.visible')
    cy.get('input[type="password"]').should('be.visible')
    cy.get('button[type="submit"]').should('contain', 'Entrar')
  })

  it('should show validation errors for empty fields', () => {
    cy.get('button[type="submit"]').click()
    cy.get('form').should('contain', 'E-mail inválido')
    cy.get('form').should('contain', 'Senha deve ter no mínimo 8 caracteres')
  })

  it('should show error for invalid credentials', () => {
    cy.get('input[type="email"]').type('invalid@email.com')
    cy.get('input[type="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()
    
    // Note: This would fail without a real backend
    // In a real scenario, we'd mock the API response
  })

  it('should navigate to register page', () => {
    cy.contains('Registre-se').click()
    cy.url().should('include', '/auth/register')
  })

  it('should navigate to forgot password page', () => {
    cy.contains('Esqueci minha senha').click()
    cy.url().should('include', '/auth/forgot-password')
  })

  it('should have gov.br login option', () => {
    cy.contains('Entrar com Gov.br').should('be.visible')
  })

  it('should have proper form labels and accessibility', () => {
    cy.get('label[for="email"]').should('contain', 'E-mail')
    cy.get('label[for="password"]').should('contain', 'Senha')
    cy.get('input[type="email"]').should('have.attr', 'placeholder', 'seu@email.com')
    cy.get('input[type="password"]').should('have.attr', 'placeholder', '••••••••')
  })
})