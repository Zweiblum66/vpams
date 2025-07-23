# MAMS E2E Testing with Cypress

This directory contains end-to-end tests for the MAMS frontend application using Cypress.

## Overview

Our E2E tests cover critical user journeys including:
- Authentication flows (login, logout, MFA, password reset)
- Asset management (upload, browse, search, download)
- Workflow automation (creation, execution, monitoring)
- Search functionality (basic, advanced, natural language)
- Collaboration features (sharing, approvals, notifications)

## Test Structure

```
cypress/
├── e2e/                    # Test specs organized by feature
│   ├── auth/              # Authentication tests
│   ├── assets/            # Asset management tests
│   ├── search/            # Search functionality tests
│   └── workflows/         # Workflow automation tests
├── fixtures/              # Test data and mock responses
├── support/               # Custom commands and utilities
│   ├── commands.ts        # Reusable test commands
│   └── e2e.ts            # Global configuration
└── config/               # Environment-specific configs
```

## Prerequisites

1. Node.js 18+ and npm installed
2. Docker and Docker Compose for backend services
3. Chrome, Firefox, or Edge browser

## Installation

From the frontend directory:

```bash
npm install
```

## Running Tests

### Quick Start

Run all E2E tests in headless mode:

```bash
npm run e2e
```

### Interactive Mode

Open Cypress Test Runner for interactive testing:

```bash
npm run e2e:open
```

### Specific Browser

Run tests in a specific browser:

```bash
npm run cypress:run:chrome
npm run cypress:run:firefox
npm run cypress:run:edge
```

### Headed Mode

Run tests with browser visible:

```bash
npm run e2e:headed
```

### Full Environment Setup

Run tests with automatic backend setup:

```bash
npm run e2e:all
```

This script will:
1. Start all backend services via Docker
2. Seed the test database
3. Build and serve the frontend
4. Run the Cypress tests
5. Clean up after completion

### Specific Test Files

Run a specific test file:

```bash
npx cypress run --spec "cypress/e2e/auth/authentication.cy.ts"
```

### Environment Configuration

Tests can run against different environments:

```bash
# Local development (default)
CYPRESS_ENVIRONMENT=local npm run e2e

# Staging environment
CYPRESS_ENVIRONMENT=staging npm run e2e
```

## Writing Tests

### Best Practices

1. **Use data-cy attributes** for element selection:
   ```typescript
   cy.get('[data-cy=submit-button]').click()
   ```

2. **Leverage custom commands** for common actions:
   ```typescript
   cy.login()
   cy.uploadAsset('path/to/file.mp4')
   ```

3. **Clean up test data** after each test:
   ```typescript
   afterEach(() => {
     cy.deleteAsset(testAssetId)
   })
   ```

4. **Use fixtures** for test data:
   ```typescript
   cy.fixture('assets/test-video.json').then((data) => {
     // Use test data
   })
   ```

5. **Test both happy and error paths**
6. **Keep tests independent** - each test should run in isolation
7. **Use meaningful test descriptions**

### Custom Commands

Available custom commands:

#### Authentication
- `cy.login(email?, password?)` - Log in with credentials
- `cy.logout()` - Log out current user
- `cy.loginAsAdmin()` - Log in as admin user

#### Assets
- `cy.uploadAsset(filePath, metadata?)` - Upload an asset
- `cy.deleteAsset(assetId)` - Delete an asset
- `cy.searchAssets(query)` - Search for assets

#### Projects
- `cy.createProject(name, description?)` - Create a project
- `cy.selectProject(projectId)` - Select a project

#### Workflows
- `cy.createWorkflow(name, steps)` - Create a workflow
- `cy.executeWorkflow(workflowId, assetId)` - Execute a workflow

#### UI Helpers
- `cy.waitForLoader()` - Wait for loading indicator to disappear
- `cy.selectFromDropdown(selector, value)` - Select dropdown option
- `cy.dragAndDrop(source, target)` - Drag and drop elements

#### API
- `cy.apiRequest(method, url, options?)` - Make API request

#### Database
- `cy.resetDatabase()` - Reset test database
- `cy.seedDatabase(fixture)` - Seed database with fixture data

## CI/CD Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Daily schedule (2 AM UTC)
- Manual workflow dispatch

GitHub Actions workflow: `.github/workflows/e2e-tests.yml`

### Test Reports

Test results are:
- Recorded to Cypress Dashboard (if configured)
- Saved as artifacts in GitHub Actions
- Posted as PR comments
- Available in mochawesome HTML format

## Debugging

### Screenshots and Videos

- Screenshots are taken automatically on failure
- Videos are recorded for all test runs
- Located in `cypress/screenshots` and `cypress/videos`

### Debug Commands

Run with debug logging:

```bash
DEBUG=cypress:* npm run e2e
```

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 8000-8013 are free
2. **Docker issues**: Run `docker-compose down` and restart
3. **Timeout errors**: Increase timeout in cypress.config.ts
4. **Authentication failures**: Check test user credentials in database

## Test Data

### Default Test Users

- **Regular User**: test@mams.local / Test123!@#
- **Admin User**: admin@mams.local / Admin123!@#

### Fixtures

Key fixtures in `cypress/fixtures/`:
- `auth/` - Authentication responses
- `assets/` - Sample assets and metadata
- `search/` - Search test data
- `workflows/` - Workflow configurations

## Performance

### Optimization Tips

1. **Parallelize tests** in CI with multiple machines
2. **Use cy.intercept()** to mock slow API calls
3. **Minimize use of cy.wait()** with fixed times
4. **Group related tests** to reduce setup/teardown

### Benchmarks

Target test execution times:
- Authentication suite: < 30s
- Asset management suite: < 2m
- Search suite: < 1m
- Workflow suite: < 3m
- Full suite: < 10m

## Contributing

1. Create feature branch
2. Write tests following patterns
3. Ensure all tests pass locally
4. Submit PR with test results

## Resources

- [Cypress Documentation](https://docs.cypress.io)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [MAMS Frontend Testing Guide](../docs/testing.md)