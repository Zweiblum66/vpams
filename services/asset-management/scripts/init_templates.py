#!/usr/bin/env python3
"""
Initialize system templates for the Asset Management Service

This script creates the default set of system templates that come
pre-installed with MAMS.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.services.template_service import ProjectTemplateService
from src.core.config import get_settings
from uuid import uuid4
import structlog

# Setup logging
logger = structlog.get_logger()

async def init_templates():
    """Initialize system templates"""
    
    settings = get_settings()
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create service with a system user ID (could be None for system operations)
        service = ProjectTemplateService(session, uuid4())
        
        try:
            logger.info("Initializing system templates...")
            
            # Initialize templates
            templates = await service.initialize_system_templates()
            
            if templates:
                logger.info(f"Created {len(templates)} system templates:")
                for template in templates:
                    logger.info(f"  - {template.name} ({template.category})")
            else:
                logger.info("System templates already exist")
                
        except Exception as e:
            logger.error(f"Failed to initialize templates: {e}")
            raise
        
    await engine.dispose()
    

if __name__ == "__main__":
    asyncio.run(init_templates())