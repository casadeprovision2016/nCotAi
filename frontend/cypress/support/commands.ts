/// <reference types="cypress" />

// Custom commands for COTAI application
declare global {
  namespace Cypress {
    interface Chainable {
      login(email: string, password: string): Chainable<void>
      logout(): Chainable<void>
      getBySel(dataTestAttribute: string, args?: any): Chainable<JQuery<HTMLElement>>
    }
  }
}

Cypress.Commands.add('login', (email: string, password: string) => {
  cy.session(
    [email, password],
    () => {
      cy.visit('/auth/login')
      cy.get('input[type="email"]').type(email)
      cy.get('input[type="password"]').type(password)
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/app')
    },
    {
      validate: () => {
        cy.getCookie('auth-token').should('exist')
      },
    }
  )
})

Cypress.Commands.add('logout', () => {
  cy.get('[data-testid="user-menu"]').click()
  cy.get('[data-testid="logout-button"]').click()
  cy.url().should('include', '/auth/login')
})

Cypress.Commands.add('getBySel', (selector, ...args) => {
  return cy.get(`[data-testid=${selector}]`, ...args)
})