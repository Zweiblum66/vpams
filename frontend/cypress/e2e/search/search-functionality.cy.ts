describe('Search Functionality', () => {
  beforeEach(() => {
    cy.login()
    // Seed test data with various asset types and metadata
    cy.seedDatabase('search/test-search-data.json')
    cy.visit('/search')
  })

  describe('Basic Search', () => {
    it('should search by keyword', () => {
      cy.get('[data-cy=search-input]').type('sunset')
      cy.get('[data-cy=search-button]').click()
      
      cy.wait('@searchAssets')
      
      // Should return relevant results
      cy.get('[data-cy=search-results]').should('exist')
      cy.get('[data-cy=result-count]').should('contain', 'results')
      
      // Each result should contain the search term
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).should('contain.text', 'sunset')
      })
    })

    it('should show no results message', () => {
      cy.get('[data-cy=search-input]').type('nonexistentasset12345')
      cy.get('[data-cy=search-button]').click()
      
      cy.wait('@searchAssets')
      cy.get('[data-cy=no-results]').should('contain', 'No results found')
    })

    it('should handle empty search', () => {
      cy.get('[data-cy=search-button]').click()
      cy.get('[data-cy=search-error]').should('contain', 'Please enter a search term')
    })

    it('should search with enter key', () => {
      cy.get('[data-cy=search-input]').type('video{enter}')
      cy.wait('@searchAssets')
      cy.get('[data-cy=search-results]').should('exist')
    })

    it('should clear search', () => {
      cy.get('[data-cy=search-input]').type('test search')
      cy.get('[data-cy=clear-search]').click()
      
      cy.get('[data-cy=search-input]').should('have.value', '')
      cy.get('[data-cy=search-results]').should('not.exist')
    })
  })

  describe('Advanced Search', () => {
    it('should toggle advanced search panel', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      cy.get('[data-cy=advanced-search-panel]').should('be.visible')
      
      cy.get('[data-cy=advanced-search-toggle]').click()
      cy.get('[data-cy=advanced-search-panel]').should('not.be.visible')
    })

    it('should search by file type', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      
      // Select video type
      cy.get('[data-cy=filter-type-video]').check()
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // All results should be videos
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=asset-type]').should('contain', 'video')
      })
    })

    it('should search by date range', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      
      // Set date range
      cy.get('[data-cy=date-from]').type('2024-01-01')
      cy.get('[data-cy=date-to]').type('2024-12-31')
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // Verify results are within date range
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=asset-date]').then(($date) => {
          const date = new Date($date.text())
          expect(date.getFullYear()).to.equal(2024)
        })
      })
    })

    it('should search by file size', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      
      // Set size range (10MB - 100MB)
      cy.get('[data-cy=size-min]').type('10')
      cy.get('[data-cy=size-min-unit]').select('MB')
      cy.get('[data-cy=size-max]').type('100')
      cy.get('[data-cy=size-max-unit]').select('MB')
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // Verify file sizes
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=asset-size]').then(($size) => {
          const sizeText = $size.text()
          const sizeMatch = sizeText.match(/(\d+\.?\d*)\s*(MB|GB)/)
          if (sizeMatch) {
            const size = parseFloat(sizeMatch[1])
            const unit = sizeMatch[2]
            
            if (unit === 'MB') {
              expect(size).to.be.gte(10).and.lte(100)
            } else if (unit === 'GB') {
              expect(size * 1024).to.be.lte(100)
            }
          }
        })
      })
    })

    it('should search by metadata fields', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      
      // Add metadata filters
      cy.get('[data-cy=add-metadata-filter]').click()
      cy.get('[data-cy=metadata-field-0]').type('camera')
      cy.get('[data-cy=metadata-value-0]').type('Canon')
      
      cy.get('[data-cy=add-metadata-filter]').click()
      cy.get('[data-cy=metadata-field-1]').type('location')
      cy.get('[data-cy=metadata-value-1]').type('New York')
      
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // Results should match metadata criteria
      cy.get('[data-cy=search-result-item]').should('have.length.greaterThan', 0)
    })

    it('should combine multiple filters', () => {
      cy.get('[data-cy=advanced-search-toggle]').click()
      
      // Search term
      cy.get('[data-cy=search-input]').type('beach')
      
      // File type
      cy.get('[data-cy=filter-type-image]').check()
      
      // Date range
      cy.get('[data-cy=date-preset-30days]').click()
      
      // Tags
      cy.get('[data-cy=tag-filter]').type('vacation{enter}summer{enter}')
      
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // Results should match all criteria
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).should('contain.text', 'beach')
        cy.wrap($item).find('[data-cy=asset-type]').should('contain', 'image')
        cy.wrap($item).find('[data-cy=asset-tags]').should('contain', 'vacation')
      })
    })
  })

  describe('Natural Language Search', () => {
    it('should understand natural language queries', () => {
      cy.get('[data-cy=search-input]').type('videos from last week about product launch')
      cy.get('[data-cy=search-button]').click()
      
      cy.wait('@searchAssets')
      
      // Should parse and apply filters
      cy.get('[data-cy=applied-filters]').should('exist')
      cy.get('[data-cy=filter-chip-type]').should('contain', 'video')
      cy.get('[data-cy=filter-chip-date]').should('contain', 'Last 7 days')
      cy.get('[data-cy=filter-chip-keyword]').should('contain', 'product launch')
    })

    it('should extract technical specifications', () => {
      cy.get('[data-cy=search-input]').type('4K videos with 60fps')
      cy.get('[data-cy=search-button]').click()
      
      cy.wait('@searchAssets')
      
      // Should filter by resolution and framerate
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=tech-specs]').should('contain', '4K')
        cy.wrap($item).find('[data-cy=tech-specs]').should('contain', '60fps')
      })
    })

    it('should understand relative dates', () => {
      const queries = [
        'photos from yesterday',
        'videos uploaded today',
        'assets from this month',
        'files created last year'
      ]
      
      queries.forEach((query) => {
        cy.get('[data-cy=search-input]').clear().type(query)
        cy.get('[data-cy=search-button]').click()
        
        cy.wait('@searchAssets')
        cy.get('[data-cy=applied-filters]').should('contain', 'Date')
        cy.get('[data-cy=clear-search]').click()
      })
    })
  })

  describe('Search Results', () => {
    beforeEach(() => {
      cy.get('[data-cy=search-input]').type('test')
      cy.get('[data-cy=search-button]').click()
      cy.wait('@searchAssets')
    })

    it('should sort search results', () => {
      // Sort by relevance (default)
      cy.get('[data-cy=sort-dropdown]').should('contain', 'Relevance')
      
      // Sort by date (newest first)
      cy.get('[data-cy=sort-dropdown]').click()
      cy.get('[data-cy=sort-date-desc]').click()
      
      cy.wait('@searchAssets')
      
      // Verify sorting
      let previousDate = new Date()
      cy.get('[data-cy=search-result-item]').each(($item) => {
        cy.wrap($item).find('[data-cy=asset-date]').then(($date) => {
          const currentDate = new Date($date.text())
          expect(currentDate.getTime()).to.be.lte(previousDate.getTime())
          previousDate = currentDate
        })
      })
    })

    it('should change results view', () => {
      // Grid view
      cy.get('[data-cy=view-grid]').click()
      cy.get('[data-cy=results-grid]').should('exist')
      cy.get('[data-cy=result-card]').should('have.length.greaterThan', 0)
      
      // List view
      cy.get('[data-cy=view-list]').click()
      cy.get('[data-cy=results-list]').should('exist')
      cy.get('[data-cy=result-row]').should('have.length.greaterThan', 0)
      
      // Compact view
      cy.get('[data-cy=view-compact]').click()
      cy.get('[data-cy=results-compact]').should('exist')
    })

    it('should preview asset from results', () => {
      cy.get('[data-cy=search-result-item]').first().within(() => {
        cy.get('[data-cy=preview-button]').click()
      })
      
      cy.get('[data-cy=preview-modal]').should('exist')
      cy.get('[data-cy=preview-player]').should('exist')
      cy.get('[data-cy=preview-metadata]').should('exist')
      
      // Close preview
      cy.get('[data-cy=close-preview]').click()
      cy.get('[data-cy=preview-modal]').should('not.exist')
    })

    it('should add asset to collection from results', () => {
      cy.get('[data-cy=search-result-item]').first().within(() => {
        cy.get('[data-cy=add-to-collection]').click()
      })
      
      cy.get('[data-cy=collection-modal]').should('exist')
      cy.get('[data-cy=collection-select]').click()
      cy.get('[data-cy=collection-option-favorites]').click()
      cy.get('[data-cy=add-to-collection-confirm]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Added to collection')
    })
  })

  describe('Saved Searches', () => {
    it('should save a search', () => {
      // Perform a search with filters
      cy.get('[data-cy=advanced-search-toggle]').click()
      cy.get('[data-cy=search-input]').type('project videos')
      cy.get('[data-cy=filter-type-video]').check()
      cy.get('[data-cy=date-preset-30days]').click()
      cy.get('[data-cy=apply-filters]').click()
      
      cy.wait('@searchAssets')
      
      // Save the search
      cy.get('[data-cy=save-search-button]').click()
      cy.get('[data-cy=save-search-modal]').should('exist')
      cy.get('[data-cy=search-name]').type('Recent Project Videos')
      cy.get('[data-cy=search-description]').type('Videos from projects in the last 30 days')
      cy.get('[data-cy=save-search-confirm]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Search saved')
    })

    it('should load saved searches', () => {
      cy.get('[data-cy=saved-searches-button]').click()
      cy.get('[data-cy=saved-searches-panel]').should('exist')
      
      // Should show saved searches
      cy.get('[data-cy=saved-search-item]').should('have.length.greaterThan', 0)
      
      // Load a saved search
      cy.get('[data-cy=saved-search-item]').first().click()
      
      cy.wait('@searchAssets')
      
      // Should apply saved filters
      cy.get('[data-cy=applied-filters]').should('exist')
    })

    it('should delete saved search', () => {
      cy.get('[data-cy=saved-searches-button]').click()
      
      cy.get('[data-cy=saved-search-item]').first().within(() => {
        cy.get('[data-cy=delete-saved-search]').click()
      })
      
      cy.get('[data-cy=confirm-delete-modal]').should('exist')
      cy.get('[data-cy=confirm-delete]').click()
      
      cy.get('[data-cy=success-toast]').should('contain', 'Search deleted')
    })
  })

  describe('Search History', () => {
    it('should show recent searches', () => {
      // Perform several searches
      const searches = ['sunset', 'mountain', 'ocean', 'city']
      
      searches.forEach((term) => {
        cy.get('[data-cy=search-input]').clear().type(term)
        cy.get('[data-cy=search-button]').click()
        cy.wait('@searchAssets')
      })
      
      // Click on search input to show history
      cy.get('[data-cy=search-input]').clear().click()
      cy.get('[data-cy=search-history]').should('exist')
      
      // Should show recent searches in reverse order
      searches.reverse().forEach((term, index) => {
        cy.get(`[data-cy=history-item-${index}]`).should('contain', term)
      })
    })

    it('should select from search history', () => {
      cy.get('[data-cy=search-input]').click()
      cy.get('[data-cy=history-item-0]').click()
      
      // Should populate search input and perform search
      cy.get('[data-cy=search-input]').should('not.have.value', '')
      cy.wait('@searchAssets')
      cy.get('[data-cy=search-results]').should('exist')
    })

    it('should clear search history', () => {
      cy.get('[data-cy=search-input]').click()
      cy.get('[data-cy=clear-history]').click()
      cy.get('[data-cy=confirm-clear-history]').click()
      
      cy.get('[data-cy=search-history]').should('not.exist')
    })
  })
})