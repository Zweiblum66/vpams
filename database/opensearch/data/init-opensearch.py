#!/usr/bin/env python3
"""
OpenSearch initialization script for MAMS
This script sets up OpenSearch indices and sample data
"""

import json
import requests
import time
from datetime import datetime, timedelta
import uuid
import sys
import os


class OpenSearchInitializer:
    def __init__(self, host='localhost', port=9200):
        self.base_url = f'http://{host}:{port}'
        self.headers = {'Content-Type': 'application/json'}
        
    def wait_for_opensearch(self, max_retries=30, delay=5):
        """Wait for OpenSearch to be ready"""
        for attempt in range(max_retries):
            try:
                response = requests.get(f'{self.base_url}/_cluster/health', 
                                      headers=self.headers, timeout=5)
                if response.status_code == 200:
                    health = response.json()
                    if health['status'] in ['green', 'yellow']:
                        print(f"OpenSearch is ready (status: {health['status']})")
                        return True
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt + 1}: OpenSearch not ready - {e}")
                
            if attempt < max_retries - 1:
                time.sleep(delay)
                
        raise Exception("OpenSearch did not become ready within timeout")
    
    def create_index(self, index_name, mapping_file):
        """Create an index with the given mapping"""
        # Check if index already exists
        response = requests.head(f'{self.base_url}/{index_name}')
        if response.status_code == 200:
            print(f"Index '{index_name}' already exists, deleting...")
            requests.delete(f'{self.base_url}/{index_name}')
        
        # Read mapping from file
        with open(mapping_file, 'r') as f:
            mapping = json.load(f)
        
        # Create index
        response = requests.put(f'{self.base_url}/{index_name}',
                              headers=self.headers,
                              json=mapping)
        
        if response.status_code in [200, 201]:
            print(f"Index '{index_name}' created successfully")
            return True
        else:
            print(f"Failed to create index '{index_name}': {response.text}")
            return False
    
    def index_document(self, index_name, doc_id, document):
        """Index a single document"""
        response = requests.put(f'{self.base_url}/{index_name}/_doc/{doc_id}',
                              headers=self.headers,
                              json=document)
        
        return response.status_code in [200, 201]
    
    def bulk_index(self, index_name, documents):
        """Bulk index multiple documents"""
        bulk_data = []
        for doc_id, document in documents.items():
            bulk_data.append(json.dumps({"index": {"_index": index_name, "_id": doc_id}}))
            bulk_data.append(json.dumps(document))
        
        bulk_body = '\n'.join(bulk_data) + '\n'
        
        response = requests.post(f'{self.base_url}/_bulk',
                               headers=self.headers,
                               data=bulk_body)
        
        if response.status_code == 200:
            result = response.json()
            errors = [item for item in result['items'] if 'error' in item.get('index', {})]
            if errors:
                print(f"Bulk indexing had {len(errors)} errors")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  Error: {error}")
            return len(errors) == 0
        else:
            print(f"Bulk indexing failed: {response.text}")
            return False
    
    def create_sample_assets(self):
        """Create sample asset documents"""
        base_date = datetime.now() - timedelta(days=30)
        
        assets = {}
        for i in range(50):
            asset_id = str(uuid.uuid4())
            content_types = ['video', 'image', 'audio', 'document']
            content_type = content_types[i % len(content_types)]
            
            # Generate realistic metadata based on content type
            metadata = {}
            if content_type == 'video':
                metadata = {
                    'width': 1920,
                    'height': 1080,
                    'duration': 120.5 + (i * 10),
                    'frame_rate': 29.97,
                    'bit_rate': 5000000,
                    'codec': 'h264'
                }
            elif content_type == 'image':
                metadata = {
                    'width': 3840,
                    'height': 2160,
                    'camera': 'Canon EOS R5',
                    'lens': 'RF 24-70mm f/2.8L',
                    'iso': 400,
                    'aperture': 'f/2.8',
                    'shutter_speed': '1/250'
                }
            elif content_type == 'audio':
                metadata = {
                    'duration': 180.0 + (i * 5),
                    'bit_rate': 320000,
                    'sample_rate': 44100,
                    'channels': 2
                }
            
            asset = {
                'asset_id': asset_id,
                'organization_id': '00000000-0000-0000-0000-000000000001',
                'project_id': '00000000-0000-0000-0000-000000000200',
                'title': f'Sample {content_type.title()} {i+1}',
                'description': f'This is a sample {content_type} asset for demonstration purposes. Asset number {i+1}.',
                'filename': f'sample_{content_type}_{i+1}.{self.get_extension(content_type)}',
                'content_type': content_type,
                'mime_type': self.get_mime_type(content_type),
                'file_extension': self.get_extension(content_type),
                'file_size': 1024000 + (i * 100000),
                'tags': [f'sample', f'{content_type}', f'demo', f'test_{i%5}'],
                'keywords': f'sample {content_type} demo test asset',
                'location': f'Sample Location {i%10}',
                'created_at': (base_date + timedelta(days=i)).isoformat(),
                'updated_at': (base_date + timedelta(days=i, hours=1)).isoformat(),
                'uploaded_at': (base_date + timedelta(days=i)).isoformat(),
                'uploaded_by': '00000000-0000-0000-0000-000000000100',
                'status': 'active',
                'metadata': metadata,
                'usage_stats': {
                    'view_count': i * 10,
                    'download_count': i * 2,
                    'share_count': i,
                    'last_accessed': (datetime.now() - timedelta(hours=i)).isoformat()
                },
                'collections': [f'collection_{i%3}'],
                'permissions': {
                    'public': i % 2 == 0,
                    'users': ['00000000-0000-0000-0000-000000000100'],
                    'groups': ['editors']
                },
                'suggest': {
                    'input': [f'Sample {content_type.title()} {i+1}', f'sample_{content_type}_{i+1}'],
                    'contexts': {
                        'content_type': content_type,
                        'project': 'demo-project'
                    }
                }
            }
            
            # Add transcription for video assets
            if content_type == 'video':
                asset['transcription'] = {
                    'text': f'This is a sample transcription for video {i+1}. The content discusses various topics related to media asset management.',
                    'language': 'en',
                    'confidence': 0.95,
                    'segments': [
                        {
                            'start': 0.0,
                            'end': 5.0,
                            'text': f'This is a sample transcription for video {i+1}.',
                            'confidence': 0.98
                        },
                        {
                            'start': 5.0,
                            'end': 10.0,
                            'text': 'The content discusses various topics related to media asset management.',
                            'confidence': 0.92
                        }
                    ]
                }
            
            # Add AI analysis
            asset['ai_analysis'] = {
                'objects': ['person', 'computer', 'desk'] if i % 3 == 0 else ['building', 'sky', 'tree'],
                'scenes': ['office', 'indoor'] if i % 2 == 0 else ['outdoor', 'nature'],
                'faces': ['person_1'] if i % 4 == 0 else [],
                'emotions': ['happy', 'neutral'],
                'colors': ['blue', 'white', 'gray'],
                'confidence_scores': {
                    'objects': 0.85,
                    'scenes': 0.92,
                    'faces': 0.78 if i % 4 == 0 else 0.0
                }
            }
            
            assets[asset_id] = asset
        
        return assets
    
    def create_sample_metadata(self):
        """Create sample metadata documents"""
        metadata_docs = {}
        
        # Common metadata fields
        fields = [
            ('title', 'string', 'Video Title'),
            ('description', 'text', 'Video Description'),
            ('director', 'string', 'John Director'),
            ('producer', 'string', 'Jane Producer'),
            ('creation_date', 'date', '2024-01-15'),
            ('location', 'string', 'New York'),
            ('camera_model', 'string', 'Canon C300'),
            ('duration', 'number', 120.5),
            ('keywords', 'array', ['video', 'production', 'demo']),
            ('copyright', 'string', 'MAMS Demo Inc.')
        ]
        
        for i, (field_name, field_type, field_value) in enumerate(fields):
            doc_id = str(uuid.uuid4())
            asset_id = f'asset_{i%10}'  # Distribute across 10 assets
            
            metadata_doc = {
                'asset_id': asset_id,
                'organization_id': '00000000-0000-0000-0000-000000000001',
                'schema_id': '00000000-0000-0000-0000-000000000400',
                'schema_name': 'basic_video_metadata',
                'metadata_type': 'descriptive',
                'field_name': field_name,
                'field_type': field_type,
                'field_value': str(field_value),
                'field_value_raw': field_value,
                'searchable': True,
                'filterable': True,
                'sortable': field_type in ['string', 'number', 'date'],
                'source': 'manual',
                'confidence': 1.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'created_by': '00000000-0000-0000-0000-000000000100',
                'validation_status': 'valid',
                'is_required': field_name in ['title', 'description'],
                'is_public': True,
                'group_name': 'basic_info' if field_name in ['title', 'description'] else 'technical',
                'display_order': i
            }
            
            # Add type-specific fields
            if field_type == 'number':
                metadata_doc['field_value_number'] = float(field_value)
            elif field_type == 'date':
                metadata_doc['field_value_date'] = field_value
            elif field_type == 'array':
                metadata_doc['field_value_array'] = field_value
            
            metadata_docs[doc_id] = metadata_doc
        
        return metadata_docs
    
    def create_sample_audit_logs(self):
        """Create sample audit log documents"""
        audit_logs = {}
        
        actions = ['create', 'read', 'update', 'delete', 'upload', 'download', 'share']
        resource_types = ['asset', 'user', 'project', 'metadata', 'workflow']
        users = [
            '00000000-0000-0000-0000-000000000100',
            '00000000-0000-0000-0000-000000000101',
            '00000000-0000-0000-0000-000000000102'
        ]
        
        for i in range(100):
            log_id = str(uuid.uuid4())
            
            log_entry = {
                'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                'log_level': 'info',
                'service': 'asset-management',
                'action': actions[i % len(actions)],
                'user_id': users[i % len(users)],
                'user_email': f'user{i%3}@mams.demo',
                'organization_id': '00000000-0000-0000-0000-000000000001',
                'session_id': str(uuid.uuid4()),
                'ip_address': f'192.168.1.{100 + (i % 50)}',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'resource_type': resource_types[i % len(resource_types)],
                'resource_id': str(uuid.uuid4()),
                'resource_name': f'Sample Resource {i}',
                'event_type': 'user_action',
                'status': 'success' if i % 10 != 0 else 'error',
                'status_code': 200 if i % 10 != 0 else 400,
                'request_id': str(uuid.uuid4()),
                'duration_ms': 50 + (i * 5),
                'bytes_transferred': 1024 * (i + 1),
                'tags': ['audit', 'user_action'],
                'environment': 'development',
                'hostname': 'mams-server-1',
                'process_id': f'pid_{i%5}',
                'thread_id': f'thread_{i%3}',
                'correlation_id': str(uuid.uuid4()),
                'security_events': {
                    'failed_login_attempts': 0 if i % 20 != 0 else 1,
                    'permission_denied': i % 30 == 0,
                    'suspicious_activity': i % 50 == 0,
                    'risk_score': 0.1 + (i % 10) * 0.1
                },
                'performance_metrics': {
                    'cpu_usage': 20.0 + (i % 50),
                    'memory_usage': 45.0 + (i % 30),
                    'disk_io': 10.0 + (i % 20),
                    'network_io': 5.0 + (i % 15),
                    'database_query_time': 2.0 + (i % 10)
                }
            }
            
            if i % 10 == 0:  # Add error details for failed requests
                log_entry['error_message'] = f'Sample error message for request {i}'
                log_entry['stack_trace'] = f'java.lang.Exception: Sample error\n\tat com.example.Service.method(Service.java:{i})'
            
            audit_logs[log_id] = log_entry
        
        return audit_logs
    
    def create_sample_search_analytics(self):
        """Create sample search analytics documents"""
        search_analytics = {}
        
        queries = [
            'video production', 'stock photos', 'marketing materials',
            'demo content', 'training videos', 'product images',
            'background music', 'presentation slides', 'interview footage',
            'brand assets', 'social media content', 'archival footage'
        ]
        
        for i in range(200):
            analytics_id = str(uuid.uuid4())
            
            query = queries[i % len(queries)]
            
            analytics_doc = {
                'timestamp': (datetime.now() - timedelta(hours=i//10)).isoformat(),
                'query_id': str(uuid.uuid4()),
                'user_id': f'user_{i%5}',
                'session_id': str(uuid.uuid4()),
                'organization_id': '00000000-0000-0000-0000-000000000001',
                'search_query': query,
                'search_type': 'text' if i % 3 == 0 else 'advanced',
                'search_filters': {
                    'content_type': ['video'] if i % 2 == 0 else ['image', 'audio'],
                    'date_range': {
                        'from': (datetime.now() - timedelta(days=30)).isoformat(),
                        'to': datetime.now().isoformat()
                    },
                    'tags': ['demo', 'sample']
                },
                'sort_options': {
                    'field': 'relevance' if i % 2 == 0 else 'date',
                    'order': 'desc'
                },
                'pagination': {
                    'page': 1,
                    'per_page': 20,
                    'offset': 0
                },
                'results': {
                    'total_hits': 50 + (i % 100),
                    'returned_hits': min(20, 50 + (i % 100)),
                    'max_score': 0.95 - (i % 50) * 0.01,
                    'has_more': (50 + (i % 100)) > 20
                },
                'performance': {
                    'query_time_ms': 50 + (i % 100),
                    'total_time_ms': 100 + (i % 200),
                    'shards': {
                        'total': 1,
                        'successful': 1,
                        'failed': 0
                    }
                },
                'clicked_results': [
                    {
                        'asset_id': str(uuid.uuid4()),
                        'position': 1,
                        'score': 0.95,
                        'clicked_at': (datetime.now() - timedelta(hours=i//10, minutes=5)).isoformat()
                    }
                ] if i % 3 == 0 else [],
                'user_behavior': {
                    'scroll_depth': 0.8,
                    'time_spent_ms': 5000 + (i * 100),
                    'refined_query': i % 5 == 0,
                    'applied_filters': i % 3 == 0,
                    'changed_sort': i % 7 == 0
                },
                'search_intent': {
                    'category': 'media_search',
                    'confidence': 0.85,
                    'entities': ['video', 'production'] if 'video' in query else ['image', 'photo'],
                    'sentiment': 'neutral'
                },
                'ip_address': f'192.168.1.{100 + (i % 50)}',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'device_info': {
                    'device_type': 'desktop',
                    'browser': 'chrome',
                    'os': 'windows',
                    'screen_size': '1920x1080'
                }
            }
            
            search_analytics[analytics_id] = analytics_doc
        
        return search_analytics
    
    def get_extension(self, content_type):
        """Get file extension for content type"""
        extensions = {
            'video': 'mp4',
            'image': 'jpg',
            'audio': 'mp3',
            'document': 'pdf'
        }
        return extensions.get(content_type, 'bin')
    
    def get_mime_type(self, content_type):
        """Get MIME type for content type"""
        mime_types = {
            'video': 'video/mp4',
            'image': 'image/jpeg',
            'audio': 'audio/mpeg',
            'document': 'application/pdf'
        }
        return mime_types.get(content_type, 'application/octet-stream')
    
    def setup_index_templates(self):
        """Set up index templates for time-based indices"""
        # Audit logs template
        audit_template = {
            "index_patterns": ["audit-logs-*"],
            "priority": 1,
            "template": {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "refresh_interval": "30s"
                    }
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "log_level": {"type": "keyword"},
                        "service": {"type": "keyword"},
                        "message": {"type": "text"}
                    }
                }
            }
        }
        
        response = requests.put(f'{self.base_url}/_index_template/audit-logs-template',
                              headers=self.headers,
                              json=audit_template)
        
        if response.status_code in [200, 201]:
            print("Audit logs index template created")
        else:
            print(f"Failed to create audit logs template: {response.text}")
    
    def create_index_aliases(self):
        """Create index aliases for easier management"""
        aliases = {
            "actions": [
                {"add": {"index": "mams-assets", "alias": "assets"}},
                {"add": {"index": "mams-metadata", "alias": "metadata"}},
                {"add": {"index": "mams-audit-logs", "alias": "audit-logs"}},
                {"add": {"index": "mams-search-analytics", "alias": "search-analytics"}}
            ]
        }
        
        response = requests.post(f'{self.base_url}/_aliases',
                               headers=self.headers,
                               json=aliases)
        
        if response.status_code == 200:
            print("Index aliases created successfully")
        else:
            print(f"Failed to create aliases: {response.text}")
    
    def refresh_indices(self):
        """Refresh all indices to make documents searchable"""
        response = requests.post(f'{self.base_url}/_refresh',
                               headers=self.headers)
        
        if response.status_code == 200:
            print("All indices refreshed successfully")
        else:
            print(f"Failed to refresh indices: {response.text}")
    
    def get_cluster_info(self):
        """Get and display cluster information"""
        try:
            # Cluster health
            health_response = requests.get(f'{self.base_url}/_cluster/health',
                                         headers=self.headers)
            if health_response.status_code == 200:
                health = health_response.json()
                print(f"\nCluster Health: {health['status']}")
                print(f"Nodes: {health['number_of_nodes']}")
                print(f"Data Nodes: {health['number_of_data_nodes']}")
                print(f"Active Shards: {health['active_shards']}")
            
            # Indices info
            indices_response = requests.get(f'{self.base_url}/_cat/indices?v&format=json',
                                          headers=self.headers)
            if indices_response.status_code == 200:
                indices = indices_response.json()
                print("\nIndices:")
                for index in indices:
                    print(f"  {index['index']}: {index['docs.count']} docs, {index['store.size']}")
                    
        except Exception as e:
            print(f"Error getting cluster info: {e}")


def main():
    """Main initialization function"""
    print("Initializing OpenSearch for MAMS...")
    
    # Initialize OpenSearch client
    opensearch = OpenSearchInitializer()
    
    try:
        # Wait for OpenSearch to be ready
        opensearch.wait_for_opensearch()
        
        # Get current directory for index files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        indices_dir = os.path.join(os.path.dirname(script_dir), 'indices')
        
        # Create indices
        indices = [
            ('mams-assets', 'assets-index.json'),
            ('mams-metadata', 'metadata-index.json'),
            ('mams-audit-logs', 'audit-logs-index.json'),
            ('mams-search-analytics', 'search-analytics-index.json')
        ]
        
        for index_name, mapping_file in indices:
            mapping_path = os.path.join(indices_dir, mapping_file)
            if os.path.exists(mapping_path):
                opensearch.create_index(index_name, mapping_path)
            else:
                print(f"Warning: Mapping file {mapping_path} not found")
        
        # Set up index templates
        opensearch.setup_index_templates()
        
        # Create sample data
        print("\nCreating sample data...")
        
        # Index sample assets
        assets = opensearch.create_sample_assets()
        if opensearch.bulk_index('mams-assets', assets):
            print(f"Indexed {len(assets)} sample assets")
        
        # Index sample metadata
        metadata = opensearch.create_sample_metadata()
        if opensearch.bulk_index('mams-metadata', metadata):
            print(f"Indexed {len(metadata)} sample metadata documents")
        
        # Index sample audit logs
        audit_logs = opensearch.create_sample_audit_logs()
        if opensearch.bulk_index('mams-audit-logs', audit_logs):
            print(f"Indexed {len(audit_logs)} sample audit logs")
        
        # Index sample search analytics
        search_analytics = opensearch.create_sample_search_analytics()
        if opensearch.bulk_index('mams-search-analytics', search_analytics):
            print(f"Indexed {len(search_analytics)} sample search analytics")
        
        # Create aliases
        opensearch.create_index_aliases()
        
        # Refresh indices
        opensearch.refresh_indices()
        
        # Display cluster info
        opensearch.get_cluster_info()
        
        print("\n" + "="*50)
        print("OPENSEARCH SETUP COMPLETE")
        print("="*50)
        print("OpenSearch is ready for MAMS!")
        print("Access OpenSearch Dashboards at: http://localhost:5601")
        print("Direct API access at: http://localhost:9200")
        
    except Exception as e:
        print(f"Error initializing OpenSearch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()