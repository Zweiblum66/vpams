describe('Workflow Automation', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/workflows')
  })

  describe('Workflow Creation', () => {
    it('should create a simple workflow', () => {
      cy.get('[data-cy=create-workflow-button]').click()
      
      // Basic workflow info
      cy.get('[data-cy=workflow-name]').type('Basic Transcoding Workflow')
      cy.get('[data-cy=workflow-description]').type('Automatically transcode uploaded videos')
      cy.get('[data-cy=workflow-trigger]').select('asset_uploaded')
      
      // Add condition
      cy.get('[data-cy=add-condition-button]').click()
      cy.get('[data-cy=condition-field]').select('asset.type')
      cy.get('[data-cy=condition-operator]').select('equals')
      cy.get('[data-cy=condition-value]').type('video')
      
      // Add transcode step
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-type]').select('transcode')
      cy.get('[data-cy=transcode-preset]').select('web_hd')
      
      // Save workflow
      cy.get('[data-cy=save-workflow-button]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow created')
      cy.url().should('match', /\/workflows\/[a-f0-9-]+/)
    })

    it('should create a complex multi-step workflow', () => {
      cy.get('[data-cy=create-workflow-button]').click()
      
      cy.get('[data-cy=workflow-name]').type('Complete Media Processing')
      cy.get('[data-cy=workflow-trigger]').select('manual')
      
      // Step 1: Extract metadata
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-0-type]').select('extract_metadata')
      cy.get('[data-cy=step-0-extractors]').click()
      cy.get('[data-cy=extractor-exif]').check()
      cy.get('[data-cy=extractor-mediainfo]').check()
      cy.get('[data-cy=extractor-ai]').check()
      
      // Step 2: Generate proxies
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-1-type]').select('generate_proxy')
      cy.get('[data-cy=step-1-qualities]').click()
      cy.get('[data-cy=proxy-low]').check()
      cy.get('[data-cy=proxy-medium]').check()
      cy.get('[data-cy=proxy-high]').check()
      
      // Step 3: AI analysis
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-2-type]').select('ai_analysis')
      cy.get('[data-cy=step-2-services]').click()
      cy.get('[data-cy=ai-transcription]').check()
      cy.get('[data-cy=ai-object-detection]').check()
      cy.get('[data-cy=ai-face-recognition]').check()
      
      // Step 4: Move to project
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-3-type]').select('move_to_project')
      cy.get('[data-cy=step-3-project]').select('auto-processed')
      
      // Step 5: Send notification
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-4-type]').select('notification')
      cy.get('[data-cy=step-4-channel]').select('email')
      cy.get('[data-cy=step-4-recipients]').type('team@mams.local')
      cy.get('[data-cy=step-4-template]').select('processing_complete')
      
      // Save workflow
      cy.get('[data-cy=save-workflow-button]').click()
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow created')
    })

    it('should validate workflow configuration', () => {
      cy.get('[data-cy=create-workflow-button]').click()
      
      // Try to save without required fields
      cy.get('[data-cy=save-workflow-button]').click()
      
      cy.get('[data-cy=validation-error]').should('contain', 'Workflow name is required')
      
      // Add name but no steps
      cy.get('[data-cy=workflow-name]').type('Invalid Workflow')
      cy.get('[data-cy=save-workflow-button]').click()
      
      cy.get('[data-cy=validation-error]').should('contain', 'At least one step is required')
    })

    it('should use workflow templates', () => {
      cy.get('[data-cy=create-workflow-button]').click()
      cy.get('[data-cy=use-template-button]').click()
      
      // Should show template gallery
      cy.get('[data-cy=template-gallery]').should('exist')
      cy.get('[data-cy=template-card]').should('have.length.greaterThan', 0)
      
      // Select a template
      cy.get('[data-cy=template-video-ingest]').click()
      cy.get('[data-cy=use-template-confirm]').click()
      
      // Should populate workflow configuration
      cy.get('[data-cy=workflow-name]').should('have.value', 'Video Ingest Workflow')
      cy.get('[data-cy=workflow-step]').should('have.length.greaterThan', 0)
      
      // Customize template
      cy.get('[data-cy=workflow-name]').clear().type('Custom Video Ingest')
      cy.get('[data-cy=save-workflow-button]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow created')
    })
  })

  describe('Workflow Management', () => {
    beforeEach(() => {
      // Seed test workflows
      cy.seedDatabase('workflows/test-workflows.json')
    })

    it('should list workflows', () => {
      cy.get('[data-cy=workflow-list]').should('exist')
      cy.get('[data-cy=workflow-item]').should('have.length.greaterThan', 0)
      
      // Each workflow should show key info
      cy.get('[data-cy=workflow-item]').first().within(() => {
        cy.get('[data-cy=workflow-name]').should('exist')
        cy.get('[data-cy=workflow-trigger]').should('exist')
        cy.get('[data-cy=workflow-status]').should('exist')
        cy.get('[data-cy=workflow-last-run]').should('exist')
      })
    })

    it('should filter workflows', () => {
      // Filter by status
      cy.get('[data-cy=filter-status]').click()
      cy.get('[data-cy=status-active]').click()
      
      cy.get('[data-cy=workflow-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=workflow-status]').should('contain', 'Active')
      })
      
      // Filter by trigger type
      cy.get('[data-cy=filter-trigger]').click()
      cy.get('[data-cy=trigger-scheduled]').click()
      
      cy.get('[data-cy=workflow-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=workflow-trigger]').should('contain', 'Scheduled')
      })
    })

    it('should edit workflow', () => {
      cy.get('[data-cy=workflow-item]').first().click()
      cy.get('[data-cy=edit-workflow-button]').click()
      
      // Update workflow
      cy.get('[data-cy=workflow-description]').clear().type('Updated description')
      
      // Add new step
      cy.get('[data-cy=add-step-button]').click()
      cy.get('[data-cy=step-type]').last().select('webhook')
      cy.get('[data-cy=webhook-url]').last().type('https://example.com/webhook')
      
      // Save changes
      cy.get('[data-cy=save-workflow-button]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow updated')
    })

    it('should enable/disable workflow', () => {
      cy.get('[data-cy=workflow-item]').first().within(() => {
        // Check current status
        cy.get('[data-cy=workflow-status]').then(($status) => {
          const isActive = $status.text().includes('Active')
          
          // Toggle status
          cy.get('[data-cy=workflow-toggle]').click()
          
          // Verify status changed
          if (isActive) {
            cy.get('[data-cy=workflow-status]').should('contain', 'Inactive')
          } else {
            cy.get('[data-cy=workflow-status]').should('contain', 'Active')
          }
        })
      })
    })

    it('should duplicate workflow', () => {
      cy.get('[data-cy=workflow-item]').first().within(() => {
        cy.get('[data-cy=workflow-actions]').click()
      })
      
      cy.get('[data-cy=duplicate-workflow]').click()
      cy.get('[data-cy=duplicate-modal]').should('exist')
      
      // Modify name
      cy.get('[data-cy=duplicate-name]').clear().type('Duplicated Workflow')
      cy.get('[data-cy=duplicate-confirm]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow duplicated')
      
      // Should show new workflow
      cy.get('[data-cy=workflow-item]').should('contain', 'Duplicated Workflow')
    })

    it('should delete workflow', () => {
      const workflowName = 'Test Workflow to Delete'
      
      // Find and delete workflow
      cy.get('[data-cy=workflow-item]').contains(workflowName).parent().within(() => {
        cy.get('[data-cy=workflow-actions]').click()
      })
      
      cy.get('[data-cy=delete-workflow]').click()
      cy.get('[data-cy=confirm-delete-modal]').should('exist')
      cy.get('[data-cy=confirm-delete]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Workflow deleted')
      
      // Should not exist in list
      cy.get('[data-cy=workflow-item]').should('not.contain', workflowName)
    })
  })

  describe('Workflow Execution', () => {
    let testWorkflowId: string
    let testAssetId: string

    beforeEach(() => {
      // Create test workflow and asset
      cy.createWorkflow('Test Execution Workflow', [
        { type: 'transcode', config: { preset: 'web_hd' } },
        { type: 'notification', config: { channel: 'email' } }
      ]).then((workflowId) => {
        testWorkflowId = workflowId
      })
      
      cy.uploadAsset('cypress/fixtures/sample-video.mp4').then((assetId) => {
        testAssetId = assetId
      })
    })

    it('should manually execute workflow', () => {
      cy.visit(`/workflows/${testWorkflowId}`)
      
      cy.get('[data-cy=execute-workflow-button]').click()
      cy.get('[data-cy=execution-modal]').should('exist')
      
      // Select asset
      cy.get('[data-cy=asset-selector]').click()
      cy.get(`[data-cy=asset-option-${testAssetId}]`).click()
      
      // Start execution
      cy.get('[data-cy=start-execution]').click()
      
      // Should show execution progress
      cy.get('[data-cy=execution-progress]').should('exist')
      cy.get('[data-cy=execution-status]').should('contain', 'Running')
      
      // Wait for completion
      cy.get('[data-cy=execution-status]', { timeout: 60000 }).should('contain', 'Completed')
    })

    it('should show execution history', () => {
      // Execute workflow first
      cy.executeWorkflow(testWorkflowId, testAssetId)
      
      cy.visit(`/workflows/${testWorkflowId}`)
      cy.get('[data-cy=execution-history-tab]').click()
      
      cy.get('[data-cy=execution-list]').should('exist')
      cy.get('[data-cy=execution-item]').should('have.length.greaterThan', 0)
      
      // View execution details
      cy.get('[data-cy=execution-item]').first().click()
      cy.get('[data-cy=execution-details]').should('exist')
      cy.get('[data-cy=execution-timeline]').should('exist')
      cy.get('[data-cy=step-status]').should('have.length', 2) // Two steps in workflow
    })

    it('should handle workflow errors', () => {
      // Create workflow with invalid step
      cy.createWorkflow('Error Test Workflow', [
        { type: 'webhook', config: { url: 'http://invalid-url-that-will-fail' } }
      ]).then((workflowId) => {
        cy.executeWorkflow(workflowId, testAssetId)
        
        cy.visit(`/workflows/${workflowId}/executions`)
        
        // Should show failed execution
        cy.get('[data-cy=execution-item]').first().within(() => {
          cy.get('[data-cy=execution-status]').should('contain', 'Failed')
        })
        
        // View error details
        cy.get('[data-cy=execution-item]').first().click()
        cy.get('[data-cy=error-details]').should('exist')
        cy.get('[data-cy=retry-button]').should('exist')
      })
    })

    it('should schedule workflow execution', () => {
      cy.visit(`/workflows/${testWorkflowId}`)
      cy.get('[data-cy=schedule-tab]').click()
      
      // Create schedule
      cy.get('[data-cy=add-schedule-button]').click()
      cy.get('[data-cy=schedule-type]').select('cron')
      cy.get('[data-cy=cron-expression]').type('0 2 * * *') // Daily at 2 AM
      cy.get('[data-cy=schedule-timezone]').select('UTC')
      
      // Set execution parameters
      cy.get('[data-cy=schedule-filter]').type('type:video')
      cy.get('[data-cy=schedule-limit]').type('10')
      
      cy.get('[data-cy=save-schedule]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Schedule created')
      cy.get('[data-cy=schedule-item]').should('exist')
    })
  })

  describe('Workflow Monitoring', () => {
    beforeEach(() => {
      cy.seedDatabase('workflows/test-executions.json')
    })

    it('should show workflow dashboard', () => {
      cy.visit('/workflows/dashboard')
      
      // Overview stats
      cy.get('[data-cy=total-workflows]').should('exist')
      cy.get('[data-cy=active-workflows]').should('exist')
      cy.get('[data-cy=executions-today]').should('exist')
      cy.get('[data-cy=success-rate]').should('exist')
      
      // Recent executions
      cy.get('[data-cy=recent-executions]').should('exist')
      cy.get('[data-cy=execution-item]').should('have.length.greaterThan', 0)
      
      // Performance metrics
      cy.get('[data-cy=performance-chart]').should('exist')
    })

    it('should filter execution logs', () => {
      cy.visit('/workflows/executions')
      
      // Filter by status
      cy.get('[data-cy=filter-status]').click()
      cy.get('[data-cy=status-failed]').click()
      
      cy.get('[data-cy=execution-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=execution-status]').should('contain', 'Failed')
      })
      
      // Filter by date
      cy.get('[data-cy=date-filter]').click()
      cy.get('[data-cy=date-today]').click()
      
      // Filter by workflow
      cy.get('[data-cy=workflow-filter]').click()
      cy.get('[data-cy=workflow-transcoding]').click()
      
      cy.get('[data-cy=execution-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=workflow-name]').should('contain', 'Transcoding')
      })
    })

    it('should export execution reports', () => {
      cy.visit('/workflows/executions')
      
      cy.get('[data-cy=export-button]').click()
      cy.get('[data-cy=export-modal]').should('exist')
      
      // Select export options
      cy.get('[data-cy=export-format]').select('csv')
      cy.get('[data-cy=export-date-range]').select('last_30_days')
      cy.get('[data-cy=include-errors]').check()
      
      cy.get('[data-cy=export-confirm]').click()
      
      // Should trigger download
      cy.get('[data-cy=export-success]').should('exist')
    })
  })

  describe('Workflow Approvals', () => {
    let approvalWorkflowId: string

    beforeEach(() => {
      // Create workflow with approval step
      cy.createWorkflow('Approval Workflow', [
        { type: 'approval', config: { approvers: ['admin@mams.local'], timeout: 24 } },
        { type: 'move_to_project', config: { project: 'approved' } }
      ]).then((workflowId) => {
        approvalWorkflowId = workflowId
      })
    })

    it('should request approval in workflow', () => {
      const assetId = 'test-asset-id'
      cy.executeWorkflow(approvalWorkflowId, assetId)
      
      // Check pending approvals
      cy.visit('/approvals')
      cy.get('[data-cy=approval-item]').should('exist')
      
      // View approval details
      cy.get('[data-cy=approval-item]').first().click()
      cy.get('[data-cy=approval-details]').should('exist')
      cy.get('[data-cy=asset-preview]').should('exist')
      cy.get('[data-cy=workflow-info]').should('exist')
      
      // Approve
      cy.get('[data-cy=approve-button]').click()
      cy.get('[data-cy=approval-comment]').type('Looks good!')
      cy.get('[data-cy=confirm-approval]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Approved')
      
      // Workflow should continue
      cy.visit(`/workflows/${approvalWorkflowId}/executions`)
      cy.get('[data-cy=execution-item]').first().within(() => {
        cy.get('[data-cy=execution-status]').should('contain', 'Completed')
      })
    })

    it('should reject approval', () => {
      const assetId = 'test-asset-id-2'
      cy.executeWorkflow(approvalWorkflowId, assetId)
      
      cy.visit('/approvals')
      cy.get('[data-cy=approval-item]').first().click()
      
      // Reject
      cy.get('[data-cy=reject-button]').click()
      cy.get('[data-cy=rejection-reason]').type('Quality issues detected')
      cy.get('[data-cy=confirm-rejection]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Rejected')
      
      // Workflow should stop
      cy.visit(`/workflows/${approvalWorkflowId}/executions`)
      cy.get('[data-cy=execution-item]').first().within(() => {
        cy.get('[data-cy=execution-status]').should('contain', 'Rejected')
      })
    })
  })
})