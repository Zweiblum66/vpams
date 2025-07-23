/// <reference types="cypress" />

// Authentication Commands
Cypress.Commands.add('login', (email?: string, password?: string) => {
  const loginEmail = email || Cypress.env('testUser').email
  const loginPassword = password || Cypress.env('testUser').password
  
  cy.visit('/login')
  cy.get('[data-cy=email-input]').type(loginEmail)
  cy.get('[data-cy=password-input]').type(loginPassword)
  cy.get('[data-cy=login-button]').click()
  
  // Wait for successful login
  cy.url().should('not.include', '/login')
  cy.window().its('localStorage.accessToken').should('exist')
})

Cypress.Commands.add('logout', () => {
  cy.get('[data-cy=user-menu]').click()
  cy.get('[data-cy=logout-button]').click()
  cy.url().should('include', '/login')
})

Cypress.Commands.add('loginAsAdmin', () => {
  cy.login(Cypress.env('adminUser').email, Cypress.env('adminUser').password)
})

// Asset Management Commands
Cypress.Commands.add('uploadAsset', (filePath: string, metadata?: Record<string, any>) => {
  cy.visit('/assets/upload')
  
  // Upload file
  cy.get('[data-cy=file-upload]').selectFile(filePath, { force: true })
  
  // Fill metadata if provided
  if (metadata) {
    Object.entries(metadata).forEach(([key, value]) => {
      cy.get(`[data-cy=metadata-${key}]`).type(value.toString())
    })
  }
  
  // Submit upload
  cy.get('[data-cy=upload-submit]').click()
  
  // Wait for upload to complete and return asset ID
  cy.wait('@uploadAsset').then((interception) => {
    return interception.response?.body.data.id
  })
})

Cypress.Commands.add('deleteAsset', (assetId: string) => {
  cy.apiRequest('DELETE', `/assets/${assetId}`)
})

// Project Commands
Cypress.Commands.add('createProject', (name: string, description?: string) => {
  cy.visit('/projects/new')
  
  cy.get('[data-cy=project-name]').type(name)
  if (description) {
    cy.get('[data-cy=project-description]').type(description)
  }
  
  cy.get('[data-cy=create-project-button]').click()
  
  // Wait for creation and return project ID
  cy.wait('@createProject').then((interception) => {
    return interception.response?.body.data.id
  })
})

Cypress.Commands.add('selectProject', (projectId: string) => {
  cy.get('[data-cy=project-selector]').click()
  cy.get(`[data-cy=project-option-${projectId}]`).click()
})

// Search Commands
Cypress.Commands.add('searchAssets', (query: string) => {
  cy.get('[data-cy=search-input]').clear().type(query)
  cy.get('[data-cy=search-button]').click()
  cy.wait('@searchAssets')
})

// Workflow Commands
Cypress.Commands.add('createWorkflow', (name: string, steps: any[]) => {
  cy.visit('/workflows/new')
  
  cy.get('[data-cy=workflow-name]').type(name)
  
  // Add workflow steps
  steps.forEach((step, index) => {
    cy.get('[data-cy=add-step-button]').click()
    cy.get(`[data-cy=step-${index}-type]`).select(step.type)
    
    if (step.config) {
      Object.entries(step.config).forEach(([key, value]) => {
        cy.get(`[data-cy=step-${index}-config-${key}]`).type(value.toString())
      })
    }
  })
  
  cy.get('[data-cy=save-workflow-button]').click()
  
  // Return workflow ID
  cy.wait('@createWorkflow').then((interception) => {
    return interception.response?.body.data.id
  })
})

Cypress.Commands.add('executeWorkflow', (workflowId: string, assetId: string) => {
  cy.apiRequest('POST', `/workflows/${workflowId}/execute`, {
    assetId: assetId
  })
})

// UI Helper Commands
Cypress.Commands.add('waitForLoader', () => {
  cy.get('[data-cy=loader]').should('not.exist')
})

Cypress.Commands.add('selectFromDropdown', (selector: string, value: string) => {
  cy.get(selector).click()
  cy.get(`[data-value="${value}"]`).click()
})

Cypress.Commands.add('dragAndDrop', (source: string, target: string) => {
  cy.get(source).trigger('dragstart')
  cy.get(target).trigger('drop')
})

// API Commands
Cypress.Commands.add('apiRequest', (method: string, url: string, options?: any) => {
  const token = window.localStorage.getItem('accessToken')
  
  return cy.request({
    method: method,
    url: `${Cypress.env('apiUrl')}${url}`,
    headers: {
      Authorization: token ? `Bearer ${token}` : undefined,
      'Content-Type': 'application/json',
      ...options?.headers
    },
    ...options
  })
})

// Database Commands
Cypress.Commands.add('resetDatabase', () => {
  cy.task('resetDatabase')
})

Cypress.Commands.add('seedDatabase', (fixture: string) => {
  cy.fixture(fixture).then((data) => {
    cy.task('seedDatabase', data)
  })
})