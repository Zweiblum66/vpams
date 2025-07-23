"""Scheduled task runner for data retention policies"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import signal
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..services.retention_service import RetentionService

logger = logging.getLogger(__name__)


class RetentionScheduler:
    """Scheduler for automated retention policy execution"""
    
    def __init__(self):
        self.running = False
        self.engine = None
        self.session_factory = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize database connection"""
        self.engine = create_async_engine(settings.database_url)
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.logger.info("Retention scheduler initialized")
        
    async def shutdown(self):
        """Clean shutdown"""
        self.running = False
        if self.engine:
            await self.engine.dispose()
        self.logger.info("Retention scheduler shut down")
    
    async def run_retention_policies(self):
        """Execute all due retention policies"""
        async with self.session_factory() as session:
            try:
                retention_service = RetentionService(session)
                
                self.logger.info("Starting retention policy execution...")
                results = await retention_service.execute_all_due_rules(dry_run=False)
                
                # Log summary
                total_deleted = sum(r.deleted_records for r in results)
                total_anonymized = sum(r.anonymized_records for r in results)
                failed = sum(1 for r in results if not r.success)
                
                self.logger.info(
                    f"Retention execution complete: "
                    f"{len(results)} rules processed, "
                    f"{total_deleted} records deleted, "
                    f"{total_anonymized} records anonymized, "
                    f"{failed} failures"
                )
                
                # Log any errors
                for result in results:
                    if not result.success:
                        self.logger.error(
                            f"Rule '{result.rule_name}' failed: "
                            f"{'; '.join(result.errors)}"
                        )
                        
            except Exception as e:
                self.logger.error(f"Error executing retention policies: {str(e)}")
    
    async def run(self, interval_minutes: int = 60):
        """Run the scheduler"""
        await self.initialize()
        self.running = True
        
        self.logger.info(f"Starting retention scheduler with {interval_minutes} minute interval")
        
        try:
            while self.running:
                try:
                    # Execute retention policies
                    await self.run_retention_policies()
                    
                    # Wait for next execution
                    await asyncio.sleep(interval_minutes * 60)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error in scheduler loop: {str(e)}")
                    # Wait a bit before retrying
                    await asyncio.sleep(60)
                    
        finally:
            await self.shutdown()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False


# Global scheduler instance
scheduler = RetentionScheduler()


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    scheduler.stop()
    sys.exit(0)


async def main():
    """Main entry point for the scheduler"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configure logging
    logging.basicConfig(
        level=settings.log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get interval from environment or use default
    interval = int(settings.retention_scheduler_interval_minutes or 60)
    
    # Run scheduler
    await scheduler.run(interval_minutes=interval)


if __name__ == "__main__":
    asyncio.run(main())