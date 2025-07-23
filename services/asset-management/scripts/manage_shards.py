#!/usr/bin/env python3
"""
Shard Management Script for MAMS Asset Management Service

This script provides utilities for managing database shards including:
- Initializing shard databases
- Checking shard health
- Rebalancing data across shards
- Monitoring shard statistics
"""

import asyncio
import click
import sys
from pathlib import Path
from typing import List, Dict, Any
import structlog

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.sharding_config import load_sharding_config, ShardDefinition
from src.db.sharding import ShardRouter, ShardManager, ShardConfig
from src.db.base import Base
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import alembic.config

logger = structlog.get_logger()


@click.group()
def cli():
    """MAMS Shard Management Utility"""
    pass


@cli.command()
@click.option('--force', is_flag=True, help='Force initialization even if databases exist')
async def init_shards(force: bool):
    """Initialize shard databases with schema"""
    config = load_sharding_config()
    
    if not config.enabled:
        click.echo("Sharding is not enabled. Set SHARDING_ENABLED=true")
        return
    
    click.echo(f"Initializing {len(config.shards)} shards...")
    
    for shard_def in config.shards:
        click.echo(f"\nProcessing shard: {shard_def.shard_id}")
        
        try:
            # Extract database name from URL
            db_url = shard_def.database_url
            if '+asyncpg' in db_url:
                sync_url = db_url.replace('+asyncpg', '')
            else:
                sync_url = db_url
            
            # Parse database name
            db_name = sync_url.split('/')[-1].split('?')[0]
            server_url = '/'.join(sync_url.split('/')[:-1])
            
            # Create database if it doesn't exist
            engine = create_engine(f"{server_url}/postgres")
            conn = engine.connect()
            conn.execute("COMMIT")  # Exit transaction
            
            exists_query = text(
                "SELECT 1 FROM pg_database WHERE datname = :dbname"
            )
            exists = conn.execute(exists_query, {"dbname": db_name}).fetchone()
            
            if exists and not force:
                click.echo(f"  Database {db_name} already exists (use --force to recreate)")
            else:
                if exists:
                    click.echo(f"  Dropping existing database {db_name}")
                    conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
                
                click.echo(f"  Creating database {db_name}")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
            
            conn.close()
            engine.dispose()
            
            # Run migrations on the shard database
            click.echo(f"  Running migrations on {db_name}")
            alembic_cfg = alembic.config.Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
            alembic.command.upgrade(alembic_cfg, "head")
            
            click.echo(f"  ✓ Shard {shard_def.shard_id} initialized successfully")
            
        except Exception as e:
            click.echo(f"  ✗ Failed to initialize shard {shard_def.shard_id}: {str(e)}")
            logger.error("shard_init_failed", shard_id=shard_def.shard_id, error=str(e))


@cli.command()
async def check_health():
    """Check health of all configured shards"""
    config = load_sharding_config()
    
    if not config.enabled:
        click.echo("Sharding is not enabled")
        return
    
    click.echo("Checking shard health...\n")
    
    healthy_count = 0
    total_count = len(config.shards)
    
    for shard_def in config.shards:
        try:
            # Test connection
            engine = create_async_engine(shard_def.database_url)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            
            await engine.dispose()
            
            status = "✓ Healthy"
            healthy_count += 1
            
        except Exception as e:
            status = f"✗ Unhealthy: {str(e)}"
        
        click.echo(f"{shard_def.shard_id}: {status}")
    
    click.echo(f"\nSummary: {healthy_count}/{total_count} shards healthy")


@cli.command()
async def show_stats():
    """Show statistics for all shards"""
    config = load_sharding_config()
    
    if not config.enabled:
        click.echo("Sharding is not enabled")
        return
    
    click.echo("Gathering shard statistics...\n")
    
    total_assets = 0
    total_size = 0
    
    for shard_def in config.shards:
        try:
            engine = create_async_engine(shard_def.database_url)
            async with engine.connect() as conn:
                # Get asset count
                result = await conn.execute(
                    text("SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as size FROM assets WHERE deleted_at IS NULL")
                )
                row = await result.fetchone()
                
                asset_count = row.count
                total_bytes = row.size
                
                total_assets += asset_count
                total_size += total_bytes
                
                # Format size
                size_gb = total_bytes / (1024 ** 3)
                
                click.echo(f"{shard_def.shard_id}:")
                click.echo(f"  Assets: {asset_count:,}")
                click.echo(f"  Size: {size_gb:.2f} GB")
                click.echo()
            
            await engine.dispose()
            
        except Exception as e:
            click.echo(f"{shard_def.shard_id}: Error - {str(e)}\n")
    
    # Summary
    total_size_gb = total_size / (1024 ** 3)
    click.echo("=" * 40)
    click.echo(f"Total Assets: {total_assets:,}")
    click.echo(f"Total Size: {total_size_gb:.2f} GB")
    click.echo(f"Average per shard: {total_assets // len(config.shards):,} assets")


@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be moved without doing it')
@click.option('--threshold', default=0.2, help='Imbalance threshold (0.0-1.0)')
async def rebalance(dry_run: bool, threshold: float):
    """Rebalance data across shards"""
    config = load_sharding_config()
    
    if not config.enabled:
        click.echo("Sharding is not enabled")
        return
    
    if not config.policy.auto_rebalance and not dry_run:
        click.echo("Auto-rebalancing is disabled. Use --dry-run to preview changes.")
        return
    
    click.echo(f"Analyzing shard balance (threshold: {threshold * 100}%)...\n")
    
    # Get current distribution
    shard_stats = {}
    total_count = 0
    
    for shard_def in config.shards:
        try:
            engine = create_async_engine(shard_def.database_url)
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT COUNT(*) as count FROM assets WHERE deleted_at IS NULL")
                )
                row = await result.fetchone()
                count = row.count
                shard_stats[shard_def.shard_id] = count
                total_count += count
            
            await engine.dispose()
            
        except Exception as e:
            click.echo(f"Error reading {shard_def.shard_id}: {str(e)}")
            return
    
    # Calculate ideal distribution
    ideal_per_shard = total_count / len(config.shards)
    
    # Find imbalanced shards
    overloaded = []
    underloaded = []
    
    for shard_id, count in shard_stats.items():
        deviation = abs(count - ideal_per_shard) / ideal_per_shard
        
        click.echo(f"{shard_id}: {count:,} assets ({deviation * 100:.1f}% deviation)")
        
        if deviation > threshold:
            if count > ideal_per_shard:
                overloaded.append((shard_id, count, count - ideal_per_shard))
            else:
                underloaded.append((shard_id, count, ideal_per_shard - count))
    
    click.echo(f"\nIdeal distribution: {ideal_per_shard:.0f} assets per shard")
    
    if not overloaded and not underloaded:
        click.echo("\n✓ Shards are balanced within threshold")
        return
    
    click.echo(f"\n⚠ Found {len(overloaded)} overloaded and {len(underloaded)} underloaded shards")
    
    if dry_run:
        click.echo("\nDry run - no changes will be made")
        
        # Calculate moves needed
        total_to_move = sum(excess for _, _, excess in overloaded)
        click.echo(f"\nWould move approximately {total_to_move:.0f} assets")
    else:
        click.echo("\nRebalancing is not yet implemented. Use --dry-run to see analysis.")


@cli.command()
@click.argument('shard_id')
async def inspect_shard(shard_id: str):
    """Inspect a specific shard in detail"""
    config = load_sharding_config()
    
    shard_def = None
    for s in config.shards:
        if s.shard_id == shard_id:
            shard_def = s
            break
    
    if not shard_def:
        click.echo(f"Shard {shard_id} not found in configuration")
        return
    
    click.echo(f"Inspecting shard: {shard_id}\n")
    
    try:
        engine = create_async_engine(shard_def.database_url)
        async with engine.connect() as conn:
            # Basic stats
            result = await conn.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_assets,
                        COUNT(DISTINCT project_id) as projects,
                        COUNT(DISTINCT owner_id) as owners,
                        COALESCE(SUM(file_size), 0) as total_size,
                        MIN(created_at) as oldest_asset,
                        MAX(created_at) as newest_asset
                    FROM assets 
                    WHERE deleted_at IS NULL
                """)
            )
            stats = await result.fetchone()
            
            click.echo(f"Total Assets: {stats.total_assets:,}")
            click.echo(f"Projects: {stats.projects:,}")
            click.echo(f"Owners: {stats.owners:,}")
            click.echo(f"Total Size: {stats.total_size / (1024**3):.2f} GB")
            click.echo(f"Oldest Asset: {stats.oldest_asset}")
            click.echo(f"Newest Asset: {stats.newest_asset}")
            
            # Asset type distribution
            click.echo("\nAsset Type Distribution:")
            result = await conn.execute(
                text("""
                    SELECT asset_type, COUNT(*) as count
                    FROM assets
                    WHERE deleted_at IS NULL
                    GROUP BY asset_type
                    ORDER BY count DESC
                """)
            )
            
            async for row in result:
                click.echo(f"  {row.asset_type}: {row.count:,}")
            
            # Storage tier distribution
            click.echo("\nStorage Tier Distribution:")
            result = await conn.execute(
                text("""
                    SELECT storage_tier, COUNT(*) as count, COALESCE(SUM(file_size), 0) as size
                    FROM assets
                    WHERE deleted_at IS NULL
                    GROUP BY storage_tier
                    ORDER BY count DESC
                """)
            )
            
            async for row in result:
                size_gb = row.size / (1024**3)
                click.echo(f"  {row.storage_tier}: {row.count:,} assets, {size_gb:.2f} GB")
        
        await engine.dispose()
        
    except Exception as e:
        click.echo(f"Error inspecting shard: {str(e)}")


def main():
    """Run async commands in sync context"""
    def run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    
    # Patch click commands to run async
    for name, cmd in cli.commands.items():
        if asyncio.iscoroutinefunction(cmd.callback):
            original = cmd.callback
            cmd.callback = lambda *args, **kwargs: run_async(original(*args, **kwargs))
    
    cli()


if __name__ == "__main__":
    main()