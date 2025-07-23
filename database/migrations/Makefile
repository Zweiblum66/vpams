# MAMS Database Migration Makefile
# Provides convenient shortcuts for common migration operations

.PHONY: help install status upgrade downgrade revision history init stamp info clean

PYTHON := python3
MIGRATE_SCRIPT := scripts/migrate.py

help: ## Show this help message
	@echo "MAMS Database Migration Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install migration dependencies
	$(PYTHON) -m pip install -r requirements.txt

status: ## Show migration status for all databases
	$(PYTHON) $(MIGRATE_SCRIPT) status

status-db: ## Show migration status for specific database (make status-db DB=users)
	$(PYTHON) $(MIGRATE_SCRIPT) status --database $(DB)

upgrade: ## Upgrade all databases to head
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade

upgrade-db: ## Upgrade specific database (make upgrade-db DB=users)
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database $(DB)

upgrade-sql: ## Generate upgrade SQL for all databases
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --sql

downgrade: ## Downgrade all databases to revision (make downgrade REV=revision_id)
	$(PYTHON) $(MIGRATE_SCRIPT) downgrade --revision $(REV)

downgrade-db: ## Downgrade specific database (make downgrade-db DB=users REV=revision_id)
	$(PYTHON) $(MIGRATE_SCRIPT) downgrade --database $(DB) --revision $(REV)

revision: ## Create new migration (make revision DB=users MSG="Add new table")
	$(PYTHON) $(MIGRATE_SCRIPT) revision --database $(DB) --message "$(MSG)"

auto-revision: ## Create auto-generated migration (make auto-revision DB=users MSG="Auto migration")
	$(PYTHON) $(MIGRATE_SCRIPT) revision --database $(DB) --message "$(MSG)" --autogenerate

history: ## Show migration history for all databases
	$(PYTHON) $(MIGRATE_SCRIPT) history

history-db: ## Show migration history for specific database (make history-db DB=users)
	$(PYTHON) $(MIGRATE_SCRIPT) history --database $(DB)

init: ## Initialize migration environment
	$(PYTHON) $(MIGRATE_SCRIPT) init

stamp: ## Stamp all databases with head revision
	$(PYTHON) $(MIGRATE_SCRIPT) stamp

stamp-db: ## Stamp specific database (make stamp-db DB=users REV=head)
	$(PYTHON) $(MIGRATE_SCRIPT) stamp --database $(DB) --revision $(REV)

info: ## Show database configuration information
	$(PYTHON) $(MIGRATE_SCRIPT) info

clean: ## Clean migration cache and temporary files
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyo" -delete

setup: install init ## Setup migration environment (install deps + initialize)

# Development shortcuts
dev-setup: setup ## Setup for development
	@echo "Migration environment ready for development"

dev-status: status ## Show development status
	@echo "Development migration status shown above"

dev-upgrade: upgrade ## Upgrade all databases for development
	@echo "All databases upgraded for development"

# Production shortcuts (use with caution)
prod-status: ## Show production status
	@echo "WARNING: This will show production migration status"
	$(PYTHON) $(MIGRATE_SCRIPT) status

prod-upgrade: ## Upgrade production databases
	@echo "WARNING: This will upgrade production databases"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade

# Database-specific shortcuts
users-status: ## Show users database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database users

users-upgrade: ## Upgrade users database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database users

assets-status: ## Show assets database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database assets

assets-upgrade: ## Upgrade assets database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database assets

metadata-status: ## Show metadata database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database metadata

metadata-upgrade: ## Upgrade metadata database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database metadata

workflow-status: ## Show workflow database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database workflow

workflow-upgrade: ## Upgrade workflow database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database workflow

rights-status: ## Show rights database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database rights

rights-upgrade: ## Upgrade rights database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database rights

audit-status: ## Show audit database status
	$(PYTHON) $(MIGRATE_SCRIPT) status --database audit

audit-upgrade: ## Upgrade audit database
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database audit

# Utility commands
check-connections: ## Check database connections
	$(PYTHON) $(MIGRATE_SCRIPT) info

reset-db: ## Reset specific database (make reset-db DB=users)
	@echo "WARNING: This will reset $(DB) database"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) $(MIGRATE_SCRIPT) downgrade --database $(DB) --revision base
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade --database $(DB)

# Docker integration
docker-upgrade: ## Upgrade databases in Docker environment
	docker-compose exec postgres psql -U mams_app -c "SELECT version();"
	$(PYTHON) $(MIGRATE_SCRIPT) upgrade

docker-status: ## Show status in Docker environment
	$(PYTHON) $(MIGRATE_SCRIPT) status