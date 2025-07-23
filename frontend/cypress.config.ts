import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    viewportWidth: 1920,
    viewportHeight: 1080,
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    
    env: {
      apiUrl: 'http://localhost:8000/api/v1',
      testUser: {
        email: 'test@mams.local',
        password: 'Test123!@#'
      },
      adminUser: {
        email: 'admin@mams.local',
        password: 'Admin123!@#'
      }
    },
    
    setupNodeEvents(on, config) {
      // implement node event listeners here
      on('task', {
        log(message) {
          console.log(message)
          return null
        },
        clearUploads() {
          // Clear test upload directory
          return null
        }
      })
      
      // Load environment-specific config
      const environmentName = config.env.ENVIRONMENT || 'local'
      const environmentConfig = require(`./cypress/config/${environmentName}.json`)
      
      return {
        ...config,
        ...environmentConfig
      }
    },
    
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    excludeSpecPattern: ['**/examples/*', '**/*.hot-update.js'],
    
    experimentalStudio: true,
    experimentalSessionAndOrigin: true,
    
    retries: {
      runMode: 2,
      openMode: 0
    }
  },
  
  component: {
    devServer: {
      framework: 'react',
      bundler: 'vite',
    },
    specPattern: 'src/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'cypress/support/component.ts'
  }
})