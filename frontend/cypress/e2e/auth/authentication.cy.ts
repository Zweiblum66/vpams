describe('Authentication', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  describe('Login', () => {
    it('should redirect unauthenticated users to login page', () => {
      cy.url().should('include', '/login')
    })

    it('should show validation errors for invalid inputs', () => {
      cy.visit('/login')
      
      // Submit empty form
      cy.get('[data-cy=login-button]').click()
      cy.get('[data-cy=email-error]').should('contain', 'Email is required')
      cy.get('[data-cy=password-error]').should('contain', 'Password is required')
      
      // Invalid email format
      cy.get('[data-cy=email-input]').type('invalid-email')
      cy.get('[data-cy=login-button]').click()
      cy.get('[data-cy=email-error]').should('contain', 'Invalid email format')
    })

    it('should show error for invalid credentials', () => {
      cy.visit('/login')
      cy.get('[data-cy=email-input]').type('wrong@email.com')
      cy.get('[data-cy=password-input]').type('wrongpassword')
      cy.get('[data-cy=login-button]').click()
      
      cy.get('[data-cy=error-alert]').should('contain', 'Invalid email or password')
    })

    it('should successfully login with valid credentials', () => {
      cy.login()
      
      // Should redirect to dashboard
      cy.url().should('include', '/dashboard')
      cy.get('[data-cy=welcome-message]').should('contain', 'Welcome')
      
      // Should have auth token in localStorage
      cy.window().its('localStorage.accessToken').should('exist')
    })

    it('should persist login on page refresh', () => {
      cy.login()
      cy.reload()
      
      // Should still be on dashboard
      cy.url().should('include', '/dashboard')
      cy.get('[data-cy=user-menu]').should('exist')
    })
  })

  describe('Logout', () => {
    beforeEach(() => {
      cy.login()
    })

    it('should successfully logout', () => {
      cy.logout()
      
      // Should redirect to login
      cy.url().should('include', '/login')
      
      // Should clear auth token
      cy.window().its('localStorage.accessToken').should('not.exist')
    })

    it('should redirect to login when accessing protected routes after logout', () => {
      cy.logout()
      cy.visit('/dashboard')
      cy.url().should('include', '/login')
    })
  })

  describe('Password Reset', () => {
    it('should send password reset email', () => {
      cy.visit('/login')
      cy.get('[data-cy=forgot-password-link]').click()
      
      cy.url().should('include', '/forgot-password')
      cy.get('[data-cy=email-input]').type('test@mams.local')
      cy.get('[data-cy=reset-button]').click()
      
      cy.get('[data-cy=success-message]').should('contain', 'Password reset email sent')
    })

    it('should reset password with valid token', () => {
      // This would typically come from an email link
      const resetToken = 'valid-reset-token'
      cy.visit(`/reset-password?token=${resetToken}`)
      
      cy.get('[data-cy=new-password-input]').type('NewPassword123!')
      cy.get('[data-cy=confirm-password-input]').type('NewPassword123!')
      cy.get('[data-cy=reset-password-button]').click()
      
      cy.get('[data-cy=success-message]').should('contain', 'Password reset successful')
      cy.url().should('include', '/login')
    })
  })

  describe('Multi-Factor Authentication', () => {
    it('should prompt for MFA code when enabled', () => {
      // Mock user with MFA enabled
      cy.intercept('POST', '**/api/v1/auth/login', {
        statusCode: 200,
        body: {
          requiresMfa: true,
          mfaToken: 'temp-mfa-token'
        }
      }).as('loginWithMfa')
      
      cy.visit('/login')
      cy.get('[data-cy=email-input]').type('mfa@mams.local')
      cy.get('[data-cy=password-input]').type('Test123!@#')
      cy.get('[data-cy=login-button]').click()
      
      cy.wait('@loginWithMfa')
      
      // Should show MFA input
      cy.url().should('include', '/mfa')
      cy.get('[data-cy=mfa-code-input]').should('exist')
      
      // Enter MFA code
      cy.get('[data-cy=mfa-code-input]').type('123456')
      cy.get('[data-cy=verify-mfa-button]').click()
      
      cy.url().should('include', '/dashboard')
    })
  })
})