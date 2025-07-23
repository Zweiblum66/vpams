#!/usr/bin/env python3
"""
Redis initialization script for MAMS development
This script sets up Redis with sample data and key structures
"""

import redis
import json
import uuid
from datetime import datetime, timedelta
import time


def connect_redis():
    """Connect to Redis with retry logic"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print(f"Connected to Redis successfully")
            return r
        except redis.ConnectionError:
            print(f"Connection attempt {attempt + 1} failed, retrying...")
            time.sleep(2)
    
    raise Exception("Could not connect to Redis after multiple attempts")


def setup_key_structures(r):
    """Set up Redis key structures and namespaces"""
    
    # Session management
    session_id = str(uuid.uuid4())
    session_data = {
        'user_id': '00000000-0000-0000-0000-000000000100',
        'username': 'admin',
        'email': 'admin@mams.demo',
        'organization_id': '00000000-0000-0000-0000-000000000001',
        'roles': ['admin'],
        'permissions': ['*'],
        'created_at': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat(),
        'ip_address': '127.0.0.1',
        'user_agent': 'Mozilla/5.0 (development)'
    }
    
    # Set session with 24-hour expiry
    r.setex(f"session:{session_id}", 86400, json.dumps(session_data))
    
    # User preferences cache
    user_preferences = {
        'theme': 'dark',
        'language': 'en',
        'timezone': 'UTC',
        'items_per_page': 20,
        'auto_play_preview': True,
        'show_thumbnails': True,
        'default_view': 'grid',
        'notifications': {
            'email': True,
            'push': False,
            'workflow': True,
            'mentions': True
        }
    }
    
    r.setex(f"user:preferences:{session_data['user_id']}", 86400, json.dumps(user_preferences))
    
    # API rate limiting
    api_rate_limits = {
        'search': 100,      # per minute
        'upload': 10,       # per minute
        'metadata': 200,    # per minute
        'download': 50      # per minute
    }
    
    for endpoint, limit in api_rate_limits.items():
        r.setex(f"rate_limit:user:{session_data['user_id']}:{endpoint}", 60, limit)
    
    # Search result caching
    search_results = {
        'query': 'demo video',
        'results': [
            {
                'id': '00000000-0000-0000-0000-000000000001',
                'title': 'Demo Video 1',
                'type': 'video',
                'duration': 120.5,
                'thumbnail': '/thumbnails/demo1.jpg',
                'created_at': '2024-01-01T10:00:00Z'
            },
            {
                'id': '00000000-0000-0000-0000-000000000002',
                'title': 'Demo Video 2',
                'type': 'video',
                'duration': 95.2,
                'thumbnail': '/thumbnails/demo2.jpg',
                'created_at': '2024-01-02T14:30:00Z'
            }
        ],
        'total': 2,
        'page': 1,
        'per_page': 20,
        'cached_at': datetime.now().isoformat()
    }
    
    search_key = f"search:query:{hash('demo video')}"
    r.setex(search_key, 300, json.dumps(search_results))  # 5 minutes cache
    
    # Asset processing queue
    processing_jobs = [
        {
            'id': str(uuid.uuid4()),
            'asset_id': '00000000-0000-0000-0000-000000000001',
            'job_type': 'transcode',
            'status': 'pending',
            'priority': 1,
            'created_at': datetime.now().isoformat(),
            'params': {
                'input_format': 'mov',
                'output_format': 'mp4',
                'quality': 'high'
            }
        },
        {
            'id': str(uuid.uuid4()),
            'asset_id': '00000000-0000-0000-0000-000000000002',
            'job_type': 'thumbnail',
            'status': 'processing',
            'priority': 2,
            'created_at': datetime.now().isoformat(),
            'params': {
                'timestamps': [5, 15, 30, 60],
                'size': 'medium'
            }
        }
    ]
    
    for job in processing_jobs:
        r.lpush('queue:processing', json.dumps(job))
    
    # Workflow task queue
    workflow_tasks = [
        {
            'id': str(uuid.uuid4()),
            'workflow_id': '00000000-0000-0000-0000-000000000500',
            'task_type': 'approval',
            'assigned_to': '00000000-0000-0000-0000-000000000103',
            'asset_id': '00000000-0000-0000-0000-000000000001',
            'due_date': (datetime.now() + timedelta(days=2)).isoformat(),
            'created_at': datetime.now().isoformat()
        }
    ]
    
    for task in workflow_tasks:
        r.lpush('queue:workflow', json.dumps(task))
    
    # Notification queue
    notifications = [
        {
            'id': str(uuid.uuid4()),
            'user_id': '00000000-0000-0000-0000-000000000100',
            'type': 'workflow_task',
            'title': 'New approval task assigned',
            'message': 'You have been assigned an approval task for Demo Video 1',
            'data': {
                'asset_id': '00000000-0000-0000-0000-000000000001',
                'workflow_id': '00000000-0000-0000-0000-000000000500'
            },
            'read': False,
            'created_at': datetime.now().isoformat()
        }
    ]
    
    for notification in notifications:
        r.lpush(f"notifications:{notification['user_id']}", json.dumps(notification))
    
    # Real-time analytics
    analytics_data = {
        'active_users': 5,
        'total_assets': 1250,
        'processing_jobs': 12,
        'storage_used_gb': 2048.5,
        'last_updated': datetime.now().isoformat()
    }
    
    r.setex('analytics:realtime', 60, json.dumps(analytics_data))
    
    # Feature flags
    feature_flags = {
        'ai_processing': True,
        'workflow_automation': True,
        'advanced_search': True,
        'collaboration_tools': True,
        'mobile_app': False,
        'beta_features': False
    }
    
    for feature, enabled in feature_flags.items():
        r.set(f"feature:flag:{feature}", str(enabled).lower())
    
    # System configuration cache
    system_config = {
        'max_file_size_mb': 5000,
        'supported_formats': ['mp4', 'mov', 'avi', 'mkv', 'jpg', 'png', 'gif', 'pdf'],
        'ai_models_enabled': ['whisper', 'yolo', 'clip'],
        'storage_tiers': {
            'hot': {'max_size_gb': 1000, 'cost_per_gb': 0.10},
            'warm': {'max_size_gb': 5000, 'cost_per_gb': 0.05},
            'cold': {'max_size_gb': 50000, 'cost_per_gb': 0.01}
        },
        'backup_retention_days': 30,
        'log_retention_days': 90
    }
    
    r.setex('config:system', 3600, json.dumps(system_config))  # 1 hour cache
    
    # Database connection pool status
    db_pools = {
        'postgresql': {'active': 5, 'idle': 15, 'max': 20},
        'mongodb': {'active': 3, 'idle': 12, 'max': 15},
        'redis': {'active': 2, 'idle': 8, 'max': 10}
    }
    
    for db_type, pool_info in db_pools.items():
        r.hmset(f"db:pool:{db_type}", pool_info)
    
    print("Redis key structures set up successfully!")


def setup_sorted_sets(r):
    """Set up sorted sets for rankings and leaderboards"""
    
    # Most popular assets (by view count)
    popular_assets = [
        ('00000000-0000-0000-0000-000000000001', 1250),
        ('00000000-0000-0000-0000-000000000002', 890),
        ('00000000-0000-0000-0000-000000000003', 567),
        ('00000000-0000-0000-0000-000000000004', 234),
        ('00000000-0000-0000-0000-000000000005', 123)
    ]
    
    for asset_id, views in popular_assets:
        r.zadd('ranking:popular_assets', {asset_id: views})
    
    # User activity scores
    user_activity = [
        ('00000000-0000-0000-0000-000000000100', 95.5),
        ('00000000-0000-0000-0000-000000000101', 78.2),
        ('00000000-0000-0000-0000-000000000102', 45.8),
        ('00000000-0000-0000-0000-000000000103', 89.1)
    ]
    
    for user_id, score in user_activity:
        r.zadd('ranking:user_activity', {user_id: score})
    
    # Recent search queries (with timestamps)
    recent_searches = [
        ('video production', time.time() - 300),
        ('stock photos', time.time() - 600),
        ('marketing materials', time.time() - 900),
        ('demo content', time.time() - 1200)
    ]
    
    for query, timestamp in recent_searches:
        r.zadd('ranking:recent_searches', {query: timestamp})
    
    print("Sorted sets created successfully!")


def setup_hash_tables(r):
    """Set up hash tables for structured data"""
    
    # Asset metadata cache
    asset_metadata = {
        'title': 'Demo Video 1',
        'description': 'Sample video for demonstration purposes',
        'duration': '120.5',
        'width': '1920',
        'height': '1080',
        'codec': 'h264',
        'bitrate': '5000000',
        'fps': '29.97',
        'created_at': '2024-01-01T10:00:00Z',
        'uploaded_by': '00000000-0000-0000-0000-000000000100'
    }
    
    r.hmset('asset:metadata:00000000-0000-0000-0000-000000000001', asset_metadata)
    r.expire('asset:metadata:00000000-0000-0000-0000-000000000001', 3600)
    
    # User stats
    user_stats = {
        'total_uploads': '45',
        'total_downloads': '128',
        'storage_used_mb': '2048',
        'last_login': datetime.now().isoformat(),
        'session_count': '156',
        'avg_session_duration': '1845'
    }
    
    r.hmset('user:stats:00000000-0000-0000-0000-000000000100', user_stats)
    
    # System metrics
    system_metrics = {
        'cpu_usage': '23.5',
        'memory_usage': '67.2',
        'disk_usage': '45.8',
        'network_io': '125.6',
        'active_connections': '234',
        'response_time_ms': '95',
        'error_rate': '0.05'
    }
    
    r.hmset('metrics:system', system_metrics)
    r.expire('metrics:system', 60)
    
    print("Hash tables created successfully!")


def setup_pub_sub_channels(r):
    """Set up pub/sub channels for real-time updates"""
    
    # Sample real-time events
    events = [
        {
            'type': 'asset_uploaded',
            'data': {
                'asset_id': '00000000-0000-0000-0000-000000000001',
                'user_id': '00000000-0000-0000-0000-000000000100',
                'filename': 'demo_video.mp4',
                'size': 1024000
            },
            'timestamp': datetime.now().isoformat()
        },
        {
            'type': 'workflow_completed',
            'data': {
                'workflow_id': '00000000-0000-0000-0000-000000000500',
                'asset_id': '00000000-0000-0000-0000-000000000001',
                'status': 'approved'
            },
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # Publish sample events to demonstrate pub/sub
    for event in events:
        r.publish('events:assets', json.dumps(event))
        r.publish('events:workflow', json.dumps(event))
    
    print("Pub/sub channels configured successfully!")


def main():
    """Main function to initialize Redis with MAMS data"""
    try:
        r = connect_redis()
        
        print("Setting up Redis for MAMS...")
        
        # Clear existing data (development only)
        r.flushall()
        
        # Set up different data structures
        setup_key_structures(r)
        setup_sorted_sets(r)
        setup_hash_tables(r)
        setup_pub_sub_channels(r)
        
        # Display summary
        print("\n" + "="*50)
        print("REDIS SETUP COMPLETE")
        print("="*50)
        print(f"Total keys created: {r.dbsize()}")
        print(f"Memory usage: {r.info()['used_memory_human']}")
        print("\nKey samples:")
        for key in r.scan_iter(count=10):
            print(f"  {key}")
        
        print("\nRedis is ready for MAMS development!")
        
    except Exception as e:
        print(f"Error initializing Redis: {e}")
        exit(1)


if __name__ == "__main__":
    main()