describe('Asset Management', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/assets')
  })

  describe('Asset Upload', () => {
    it('should upload a video file', () => {
      cy.get('[data-cy=upload-button]').click()
      
      // Select file
      cy.get('[data-cy=file-upload]').selectFile('cypress/fixtures/sample-video.mp4')
      
      // Fill metadata
      cy.get('[data-cy=metadata-title]').type('Test Video')
      cy.get('[data-cy=metadata-description]').type('This is a test video upload')
      cy.selectFromDropdown('[data-cy=metadata-type]', 'video')
      
      // Add tags
      cy.get('[data-cy=tag-input]').type('test{enter}cypress{enter}e2e{enter}')
      
      // Submit upload
      cy.get('[data-cy=upload-submit]').click()
      
      // Wait for upload to complete
      cy.get('[data-cy=upload-progress]').should('exist')
      cy.get('[data-cy=upload-success]', { timeout: 30000 }).should('exist')
      
      // Should redirect to asset detail page
      cy.url().should('match', /\/assets\/[a-f0-9-]+/)
      cy.get('[data-cy=asset-title]').should('contain', 'Test Video')
    })

    it('should upload multiple files', () => {
      cy.get('[data-cy=upload-button]').click()
      
      // Select multiple files
      cy.get('[data-cy=file-upload]').selectFile([
        'cypress/fixtures/sample-video.mp4',
        'cypress/fixtures/sample-image.jpg',
        'cypress/fixtures/sample-audio.mp3'
      ])
      
      // Should show batch upload interface
      cy.get('[data-cy=batch-upload-list]').should('exist')
      cy.get('[data-cy=batch-upload-item]').should('have.length', 3)
      
      // Apply metadata to all
      cy.get('[data-cy=apply-to-all-checkbox]').check()
      cy.selectFromDropdown('[data-cy=metadata-project]', 'test-project')
      cy.get('[data-cy=metadata-copyright]').type('Test Copyright')
      
      // Start batch upload
      cy.get('[data-cy=batch-upload-submit]').click()
      
      // Monitor progress
      cy.get('[data-cy=batch-progress]').should('exist')
      cy.get('[data-cy=batch-complete]', { timeout: 60000 }).should('exist')
    })

    it('should validate file types', () => {
      cy.get('[data-cy=upload-button]').click()
      
      // Try to upload unsupported file
      cy.get('[data-cy=file-upload]').selectFile('cypress/fixtures/unsupported.xyz')
      
      cy.get('[data-cy=file-error]').should('contain', 'Unsupported file type')
    })

    it('should handle upload errors gracefully', () => {
      // Mock upload failure
      cy.intercept('POST', '**/api/v1/assets/upload', {
        statusCode: 500,
        body: { error: 'Upload failed' }
      }).as('failedUpload')
      
      cy.get('[data-cy=upload-button]').click()
      cy.get('[data-cy=file-upload]').selectFile('cypress/fixtures/sample-video.mp4')
      cy.get('[data-cy=upload-submit]').click()
      
      cy.wait('@failedUpload')
      cy.get('[data-cy=upload-error]').should('contain', 'Upload failed')
      cy.get('[data-cy=retry-button]').should('exist')
    })
  })

  describe('Asset Browsing', () => {
    beforeEach(() => {
      // Seed some test assets
      cy.seedDatabase('assets/test-assets.json')
    })

    it('should display asset grid view', () => {
      cy.get('[data-cy=view-toggle-grid]').click()
      cy.get('[data-cy=asset-grid]').should('exist')
      cy.get('[data-cy=asset-card]').should('have.length.greaterThan', 0)
      
      // Each card should have thumbnail and basic info
      cy.get('[data-cy=asset-card]').first().within(() => {
        cy.get('[data-cy=asset-thumbnail]').should('exist')
        cy.get('[data-cy=asset-name]').should('exist')
        cy.get('[data-cy=asset-duration]').should('exist')
        cy.get('[data-cy=asset-size]').should('exist')
      })
    })

    it('should display asset list view', () => {
      cy.get('[data-cy=view-toggle-list]').click()
      cy.get('[data-cy=asset-list]').should('exist')
      cy.get('[data-cy=asset-row]').should('have.length.greaterThan', 0)
      
      // List should have sortable columns
      cy.get('[data-cy=sort-name]').click()
      cy.get('[data-cy=sort-indicator-name]').should('have.class', 'asc')
      
      cy.get('[data-cy=sort-name]').click()
      cy.get('[data-cy=sort-indicator-name]').should('have.class', 'desc')
    })

    it('should paginate results', () => {
      // Assuming we have more than 20 assets
      cy.get('[data-cy=pagination]').should('exist')
      cy.get('[data-cy=page-info]').should('contain', 'Page 1 of')
      
      // Navigate to next page
      cy.get('[data-cy=next-page]').click()
      cy.get('[data-cy=page-info]').should('contain', 'Page 2 of')
      
      // Navigate to specific page
      cy.get('[data-cy=page-3]').click()
      cy.get('[data-cy=page-info]').should('contain', 'Page 3 of')
    })

    it('should filter assets by type', () => {
      cy.get('[data-cy=filter-type]').click()
      cy.get('[data-cy=filter-type-video]').click()
      
      // Should only show video assets
      cy.get('[data-cy=asset-card]').each(($card) => {
        cy.wrap($card).find('[data-cy=asset-type-icon]').should('have.class', 'video')
      })
      
      // Clear filter
      cy.get('[data-cy=clear-filters]').click()
      cy.get('[data-cy=asset-card]').should('have.length.greaterThan', 0)
    })

    it('should filter assets by date range', () => {
      cy.get('[data-cy=filter-date]').click()
      
      // Select last 7 days
      cy.get('[data-cy=date-preset-7days]').click()
      
      // Verify results are within date range
      cy.get('[data-cy=asset-created-date]').each(($date) => {
        const date = new Date($date.text())
        const sevenDaysAgo = new Date()
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
        
        expect(date.getTime()).to.be.greaterThan(sevenDaysAgo.getTime())
      })
    })
  })

  describe('Asset Details', () => {
    let testAssetId: string

    beforeEach(() => {
      // Create a test asset
      cy.uploadAsset('cypress/fixtures/sample-video.mp4', {
        title: 'Detail Test Video',
        description: 'Video for testing asset details'
      }).then((assetId) => {
        testAssetId = assetId
        cy.visit(`/assets/${assetId}`)
      })
    })

    it('should display asset details', () => {
      // Header information
      cy.get('[data-cy=asset-title]').should('contain', 'Detail Test Video')
      cy.get('[data-cy=asset-description]').should('contain', 'Video for testing asset details')
      
      // Technical information
      cy.get('[data-cy=tech-info-tab]').click()
      cy.get('[data-cy=video-codec]').should('exist')
      cy.get('[data-cy=video-resolution]').should('exist')
      cy.get('[data-cy=video-framerate]').should('exist')
      cy.get('[data-cy=video-bitrate]').should('exist')
      
      // File information
      cy.get('[data-cy=file-info-tab]').click()
      cy.get('[data-cy=file-size]').should('exist')
      cy.get('[data-cy=file-format]').should('exist')
      cy.get('[data-cy=upload-date]').should('exist')
      cy.get('[data-cy=file-path]').should('exist')
    })

    it('should play video preview', () => {
      cy.get('[data-cy=video-player]').should('exist')
      cy.get('[data-cy=play-button]').click()
      
      // Video should be playing
      cy.get('video').should('have.prop', 'paused', false)
      
      // Test player controls
      cy.get('[data-cy=pause-button]').click()
      cy.get('video').should('have.prop', 'paused', true)
      
      // Seek to specific time
      cy.get('[data-cy=timeline-slider]').click('center')
      cy.get('[data-cy=current-time]').should('not.contain', '0:00')
    })

    it('should edit asset metadata', () => {
      cy.get('[data-cy=edit-metadata-button]').click()
      
      // Update fields
      cy.get('[data-cy=metadata-title]').clear().type('Updated Video Title')
      cy.get('[data-cy=metadata-description]').clear().type('Updated description')
      
      // Add custom metadata
      cy.get('[data-cy=add-custom-field]').click()
      cy.get('[data-cy=custom-field-key]').type('director')
      cy.get('[data-cy=custom-field-value]').type('John Doe')
      
      // Save changes
      cy.get('[data-cy=save-metadata]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Metadata updated')
      cy.get('[data-cy=asset-title]').should('contain', 'Updated Video Title')
    })

    it('should manage asset versions', () => {
      cy.get('[data-cy=versions-tab]').click()
      
      // Upload new version
      cy.get('[data-cy=upload-version-button]').click()
      cy.get('[data-cy=version-file-upload]').selectFile('cypress/fixtures/sample-video-v2.mp4')
      cy.get('[data-cy=version-notes]').type('Updated color correction')
      cy.get('[data-cy=upload-version-submit]').click()
      
      // Wait for upload
      cy.get('[data-cy=version-upload-success]', { timeout: 30000 }).should('exist')
      
      // Should show version history
      cy.get('[data-cy=version-list]').should('exist')
      cy.get('[data-cy=version-item]').should('have.length', 2)
      
      // Switch to previous version
      cy.get('[data-cy=version-item]').last().within(() => {
        cy.get('[data-cy=make-current-button]').click()
      })
      
      cy.get('[data-cy=confirm-version-change]').click()
      cy.get('[data-cy=current-version-indicator]').should('exist')
    })

    it('should download asset', () => {
      cy.get('[data-cy=download-button]').click()
      
      // Should show download options
      cy.get('[data-cy=download-original]').should('exist')
      cy.get('[data-cy=download-proxy-high]').should('exist')
      cy.get('[data-cy=download-proxy-low]').should('exist')
      
      // Download original
      cy.get('[data-cy=download-original]').click()
      
      // Verify download started (checking for file download is browser-specific)
      cy.get('[data-cy=download-started-toast]').should('exist')
    })

    afterEach(() => {
      // Clean up test asset
      if (testAssetId) {
        cy.deleteAsset(testAssetId)
      }
    })
  })

  describe('Asset Actions', () => {
    let testAssets: string[] = []

    beforeEach(() => {
      // Create multiple test assets
      const assetPromises = [
        cy.uploadAsset('cypress/fixtures/sample-video.mp4', { title: 'Test Video 1' }),
        cy.uploadAsset('cypress/fixtures/sample-image.jpg', { title: 'Test Image 1' }),
        cy.uploadAsset('cypress/fixtures/sample-audio.mp3', { title: 'Test Audio 1' })
      ]
      
      cy.wrap(Promise.all(assetPromises)).then((assetIds) => {
        testAssets = assetIds as string[]
      })
    })

    it('should select multiple assets', () => {
      cy.visit('/assets')
      
      // Select all assets
      cy.get('[data-cy=select-all-checkbox]').check()
      cy.get('[data-cy=selected-count]').should('contain', '3 selected')
      
      // Deselect one
      cy.get('[data-cy=asset-checkbox]').first().uncheck()
      cy.get('[data-cy=selected-count]').should('contain', '2 selected')
      
      // Clear selection
      cy.get('[data-cy=clear-selection]').click()
      cy.get('[data-cy=selected-count]').should('not.exist')
    })

    it('should delete assets', () => {
      cy.visit('/assets')
      
      // Select first asset
      cy.get('[data-cy=asset-checkbox]').first().check()
      
      // Delete
      cy.get('[data-cy=bulk-delete-button]').click()
      cy.get('[data-cy=confirm-delete-modal]').should('exist')
      cy.get('[data-cy=confirm-delete-button]').click()
      
      cy.get('[data-cy=delete-success-toast]').should('exist')
      
      // Asset should be removed from list
      cy.get('[data-cy=asset-card]').should('have.length', 2)
    })

    it('should move assets to project', () => {
      cy.visit('/assets')
      
      // Select all assets
      cy.get('[data-cy=select-all-checkbox]').check()
      
      // Move to project
      cy.get('[data-cy=bulk-move-button]').click()
      cy.get('[data-cy=project-selector]').click()
      cy.get('[data-cy=project-option-test-project]').click()
      cy.get('[data-cy=move-confirm-button]').click()
      
      cy.get('[data-cy=move-success-toast]').should('contain', '3 assets moved')
    })

    it('should share assets', () => {
      cy.visit('/assets')
      
      // Select an asset
      cy.get('[data-cy=asset-checkbox]').first().check()
      
      // Share
      cy.get('[data-cy=share-button]').click()
      cy.get('[data-cy=share-modal]').should('exist')
      
      // Add recipient
      cy.get('[data-cy=share-email-input]').type('colleague@mams.local')
      cy.get('[data-cy=share-permission]').select('view')
      cy.get('[data-cy=share-expiry]').type('2024-12-31')
      
      // Generate share link
      cy.get('[data-cy=generate-link-button]').click()
      cy.get('[data-cy=share-link]').should('exist')
      
      // Copy link
      cy.get('[data-cy=copy-link-button]').click()
      cy.get('[data-cy=link-copied-toast]').should('exist')
    })

    afterEach(() => {
      // Clean up test assets
      testAssets.forEach(assetId => {
        cy.deleteAsset(assetId)
      })
    })
  })
})