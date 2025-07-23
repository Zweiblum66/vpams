// ***********************************************************
// This file is processed and loaded automatically before your test files.
// You can change the location of this file or turn off loading support files
// with the 'supportFile' configuration option.
// ***********************************************************

// Import commands.ts using ES2015 syntax:
import './commands'

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Add global TypeScript types
declare global {
  namespace Cypress {
    interface Chainable {
      // Authentication commands
      login(email?: string, password?: string): Chainable<void>
      logout(): Chainable<void>
      loginAsAdmin(): Chainable<void>
      
      // Asset management commands
      uploadAsset(filePath: string, metadata?: Record<string, any>): Chainable<string>
      deleteAsset(assetId: string): Chainable<void>
      
      // Project commands
      createProject(name: string, description?: string): Chainable<string>
      selectProject(projectId: string): Chainable<void>
      
      // Search commands
      searchAssets(query: string): Chainable<void>
      
      // Workflow commands
      createWorkflow(name: string, steps: any[]): Chainable<string>
      executeWorkflow(workflowId: string, assetId: string): Chainable<void>
      
      // UI helper commands
      waitForLoader(): Chainable<void>
      selectFromDropdown(selector: string, value: string): Chainable<void>
      dragAndDrop(source: string, target: string): Chainable<void>
      
      // API commands
      apiRequest(method: string, url: string, options?: any): Chainable<any>
      
      // Database commands
      resetDatabase(): Chainable<void>
      seedDatabase(fixture: string): Chainable<void>
    }
  }
}

// Prevent TypeScript from reading file as legacy script
export {}

// Global before each hook
beforeEach(() => {
  // Clear local storage and session storage
  cy.clearLocalStorage()
  cy.clearCookies()
  
  // Set up intercepts for common API calls
  cy.intercept('GET', '**/api/v1/health', { fixture: 'health.json' }).as('healthCheck')
  cy.intercept('POST', '**/api/v1/auth/login', { fixture: 'auth/login.json' }).as('login')
  cy.intercept('GET', '**/api/v1/users/me', { fixture: 'users/me.json' }).as('getMe')
})

// Handle uncaught exceptions
Cypress.on('uncaught:exception', (err, runnable) => {
  // Return false to prevent the test from failing
  // Log the error for debugging
  console.error('Uncaught exception:', err)
  return false
})