#!/usr/bin/env python3
"""
Example script demonstrating the MAMS Ingest Scheduling functionality

This script shows how to create, manage, and monitor scheduled ingests
using the MAMS Ingest Service API.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional


class IngestSchedulerClient:
    """Client for interacting with the MAMS Ingest Scheduler API"""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_scheduled_ingest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new scheduled ingest configuration"""
        async with self.session.post(
            f"{self.base_url}/api/v1/scheduled-ingests",
            json=config
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def list_scheduled_ingests(self) -> Dict[str, Any]:
        """List all scheduled ingest configurations"""
        async with self.session.get(
            f"{self.base_url}/api/v1/scheduled-ingests"
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_scheduled_ingest(self, ingest_id: str) -> Dict[str, Any]:
        """Get a specific scheduled ingest configuration"""
        async with self.session.get(
            f"{self.base_url}/api/v1/scheduled-ingests/{ingest_id}"
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def update_scheduled_ingest(
        self,
        ingest_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a scheduled ingest configuration"""
        async with self.session.put(
            f"{self.base_url}/api/v1/scheduled-ingests/{ingest_id}",
            json=config
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def delete_scheduled_ingest(self, ingest_id: str) -> bool:
        """Delete a scheduled ingest configuration"""
        async with self.session.delete(
            f"{self.base_url}/api/v1/scheduled-ingests/{ingest_id}"
        ) as response:
            return response.status == 200
    
    async def trigger_scheduled_ingest(self, ingest_id: str) -> Dict[str, Any]:
        """Manually trigger a scheduled ingest"""
        async with self.session.post(
            f"{self.base_url}/api/v1/scheduled-ingests/{ingest_id}/run"
        ) as response:
            response.raise_for_status()
            return await response.json()
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        async with self.session.get(
            f"{self.base_url}/api/v1/scheduler-stats"
        ) as response:
            response.raise_for_status()
            return await response.json()


async def example_daily_news_archive():
    """Example: Set up daily news archive ingestion"""
    print("🗞️  Creating daily news archive schedule...")
    
    config = {
        "name": "Daily News Archive",
        "source_path": "/watch/news/archive",
        "destination_project_id": "news-project-123",
        "cron_expression": "0 2 * * *",  # Every day at 2 AM
        "enabled": True,
        "metadata_template": {
            "category": "news",
            "retention_policy": "30_days",
            "source": "archive_system"
        },
        "tags": ["automated", "news", "archive"],
        "priority": "normal",
        "auto_generate_proxies": True,
        "preserve_folder_structure": True
    }
    
    async with IngestSchedulerClient() as client:
        try:
            result = await client.create_scheduled_ingest(config)
            print(f"✅ Created scheduled ingest: {result['id']}")
            print(f"   Name: {result['name']}")
            print(f"   Schedule: {result['cron_expression']}")
            return result['id']
        except Exception as e:
            print(f"❌ Failed to create schedule: {e}")
            return None


async def example_hourly_breaking_news():
    """Example: Set up hourly breaking news monitoring"""
    print("🚨 Creating hourly breaking news monitor...")
    
    config = {
        "name": "Breaking News Monitor",
        "source_path": "/incoming/breaking",
        "destination_project_id": "news-urgent",
        "cron_expression": "0 * * * *",  # Every hour
        "enabled": True,
        "metadata_template": {
            "category": "breaking_news",
            "priority": "urgent",
            "auto_publish": True
        },
        "tags": ["breaking", "news", "urgent"],
        "priority": "urgent",
        "auto_generate_proxies": True,
        "preserve_folder_structure": False
    }
    
    async with IngestSchedulerClient() as client:
        try:
            result = await client.create_scheduled_ingest(config)
            print(f"✅ Created breaking news monitor: {result['id']}")
            return result['id']
        except Exception as e:
            print(f"❌ Failed to create monitor: {e}")
            return None


async def example_weekly_backup():
    """Example: Set up weekly backup ingestion"""
    print("💾 Creating weekly backup schedule...")
    
    config = {
        "name": "Weekly Backup Ingest",
        "source_path": "/backup/weekly",
        "destination_project_id": "backup-project",
        "cron_expression": "0 0 * * 0",  # Every Sunday at midnight
        "enabled": True,
        "metadata_template": {
            "backup_type": "weekly",
            "retention": "1_year",
            "verified": True
        },
        "tags": ["backup", "weekly", "archive"],
        "priority": "low",
        "auto_generate_proxies": False,
        "preserve_folder_structure": True
    }
    
    async with IngestSchedulerClient() as client:
        try:
            result = await client.create_scheduled_ingest(config)
            print(f"✅ Created weekly backup: {result['id']}")
            return result['id']
        except Exception as e:
            print(f"❌ Failed to create backup schedule: {e}")
            return None


async def example_batch_processing():
    """Example: Set up multiple related schedules"""
    print("📦 Creating batch processing schedules...")
    
    schedules = [
        {
            "name": "Morning Sports Highlights",
            "source_path": "/sports/highlights/morning",
            "cron_expression": "0 6 * * *",  # 6 AM daily
            "metadata_template": {"category": "sports", "time_slot": "morning"}
        },
        {
            "name": "Evening Sports Recap",
            "source_path": "/sports/recap/evening", 
            "cron_expression": "0 18 * * *",  # 6 PM daily
            "metadata_template": {"category": "sports", "time_slot": "evening"}
        },
        {
            "name": "Weekend Sports Summary",
            "source_path": "/sports/summary/weekend",
            "cron_expression": "0 20 * * 0",  # 8 PM on Sundays
            "metadata_template": {"category": "sports", "time_slot": "weekend"}
        }
    ]
    
    created_ids = []
    
    async with IngestSchedulerClient() as client:
        for schedule in schedules:
            base_config = {
                "destination_project_id": "sports-project",
                "enabled": True,
                "tags": ["sports", "automated"],
                "priority": "normal",
                "auto_generate_proxies": True,
                "preserve_folder_structure": True
            }
            
            # Merge with base config
            config = {**base_config, **schedule}
            
            try:
                result = await client.create_scheduled_ingest(config)
                created_ids.append(result['id'])
                print(f"✅ Created: {schedule['name']} ({result['id']})")
            except Exception as e:
                print(f"❌ Failed to create {schedule['name']}: {e}")
    
    return created_ids


async def example_monitor_schedules():
    """Example: Monitor scheduled ingests"""
    print("📊 Monitoring scheduled ingests...")
    
    async with IngestSchedulerClient() as client:
        try:
            # Get scheduler statistics
            stats = await client.get_scheduler_stats()
            print(f"📈 Scheduler Status:")
            print(f"   Running: {stats['is_running']}")
            print(f"   Total Schedules: {stats['total_scheduled_ingests']}")
            print(f"   Active Schedules: {stats['active_scheduled_ingests']}")
            print(f"   Scheduled Jobs: {stats['scheduled_jobs']}")
            
            # List all scheduled ingests
            ingests = await client.list_scheduled_ingests()
            print(f"\n📋 Scheduled Ingests ({len(ingests)}):")
            
            for ingest in ingests:
                status = "🟢 Enabled" if ingest['enabled'] else "🔴 Disabled"
                print(f"   {status} {ingest['name']}")
                print(f"      Schedule: {ingest['cron_expression']}")
                if ingest.get('last_execution'):
                    print(f"      Last Run: {ingest['last_execution']}")
                print()
            
            # Show next run times
            if 'next_run_times' in stats and stats['next_run_times']:
                print("⏰ Next Run Times:")
                for job in stats['next_run_times']:
                    print(f"   {job['job_name']}: {job['next_run_time']}")
        
        except Exception as e:
            print(f"❌ Failed to get monitoring data: {e}")


async def example_manage_schedule(schedule_id: str):
    """Example: Manage an existing schedule"""
    print(f"🔧 Managing schedule {schedule_id}...")
    
    async with IngestSchedulerClient() as client:
        try:
            # Get current configuration
            current = await client.get_scheduled_ingest(schedule_id)
            print(f"📄 Current config: {current['name']}")
            print(f"   Schedule: {current['cron_expression']}")
            print(f"   Enabled: {current['enabled']}")
            
            # Update the schedule (example: disable temporarily)
            updated_config = {
                **current,
                "enabled": False,
                "metadata_template": {
                    **current.get('metadata_template', {}),
                    "maintenance_mode": True
                }
            }
            
            result = await client.update_scheduled_ingest(schedule_id, updated_config)
            print(f"✅ Updated schedule - now disabled for maintenance")
            
            # Manually trigger execution
            print("🚀 Manually triggering execution...")
            trigger_result = await client.trigger_scheduled_ingest(schedule_id)
            print(f"✅ Manual trigger successful: {trigger_result['message']}")
            
            # Re-enable the schedule
            updated_config['enabled'] = True
            del updated_config['metadata_template']['maintenance_mode']
            
            await client.update_scheduled_ingest(schedule_id, updated_config)
            print("✅ Re-enabled schedule")
            
        except Exception as e:
            print(f"❌ Failed to manage schedule: {e}")


async def example_cleanup_schedules(schedule_ids: list):
    """Example: Clean up created schedules"""
    print("🧹 Cleaning up created schedules...")
    
    async with IngestSchedulerClient() as client:
        for schedule_id in schedule_ids:
            try:
                success = await client.delete_scheduled_ingest(schedule_id)
                if success:
                    print(f"✅ Deleted schedule: {schedule_id}")
                else:
                    print(f"❌ Failed to delete schedule: {schedule_id}")
            except Exception as e:
                print(f"❌ Error deleting {schedule_id}: {e}")


async def main():
    """Main example function demonstrating all scheduling features"""
    print("🎬 MAMS Ingest Scheduling Examples")
    print("=" * 50)
    
    created_ids = []
    
    try:
        # Create various types of scheduled ingests
        news_id = await example_daily_news_archive()
        if news_id:
            created_ids.append(news_id)
        
        print()
        
        breaking_id = await example_hourly_breaking_news()
        if breaking_id:
            created_ids.append(breaking_id)
        
        print()
        
        backup_id = await example_weekly_backup()
        if backup_id:
            created_ids.append(backup_id)
        
        print()
        
        batch_ids = await example_batch_processing()
        created_ids.extend(batch_ids)
        
        print()
        
        # Monitor the created schedules
        await example_monitor_schedules()
        
        print()
        
        # Manage one of the schedules
        if created_ids:
            await example_manage_schedule(created_ids[0])
        
        print()
        print("✅ All examples completed successfully!")
        
        # Ask user if they want to clean up
        print("\n🤔 Would you like to clean up the created schedules? (y/N)")
        response = input().strip().lower()
        
        if response in ['y', 'yes']:
            await example_cleanup_schedules(created_ids)
        else:
            print("📝 Schedules left running. You can manage them via the API.")
            print("   Schedule IDs:", created_ids)
    
    except Exception as e:
        print(f"❌ Example failed: {e}")
        if created_ids:
            print("🧹 Attempting cleanup...")
            await example_cleanup_schedules(created_ids)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())