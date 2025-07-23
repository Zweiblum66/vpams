"""
Grafana dashboard configurations for MAMS performance monitoring.

Creates and manages Grafana dashboards for system metrics,
application performance, and user experience monitoring.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import asyncio

logger = logging.getLogger(__name__)


class GrafanaDashboardManager:
    """Manages Grafana dashboards for MAMS monitoring."""
    
    def __init__(
        self,
        grafana_url: str,
        api_key: str,
        org_id: int = 1
    ):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.org_id = org_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def create_all_dashboards(self) -> Dict[str, Any]:
        """Create all MAMS monitoring dashboards."""
        results = {}
        
        dashboards = [
            ('system_overview', self._create_system_overview_dashboard()),
            ('application_performance', self._create_application_performance_dashboard()),
            ('web_vitals', self._create_web_vitals_dashboard()),
            ('business_metrics', self._create_business_metrics_dashboard()),
            ('error_monitoring', self._create_error_monitoring_dashboard()),
            ('user_experience', self._create_user_experience_dashboard())
        ]
        
        async with httpx.AsyncClient() as client:
            for name, dashboard_config in dashboards:
                try:
                    result = await self._create_or_update_dashboard(
                        client, name, dashboard_config
                    )
                    results[name] = result
                    logger.info(f"Successfully created/updated dashboard: {name}")
                except Exception as e:
                    logger.error(f"Failed to create dashboard {name}: {e}")
                    results[name] = {'error': str(e)}
        
        return results
    
    async def _create_or_update_dashboard(
        self,
        client: httpx.AsyncClient,
        name: str,
        dashboard_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create or update a Grafana dashboard."""
        # Check if dashboard exists
        search_url = f"{self.grafana_url}/api/search"
        search_response = await client.get(
            search_url,
            headers=self.headers,
            params={'query': dashboard_config['title']}
        )
        
        existing_dashboards = search_response.json()
        dashboard_uid = None
        
        for dashboard in existing_dashboards:
            if dashboard['title'] == dashboard_config['title']:
                dashboard_uid = dashboard['uid']
                break
        
        # Create dashboard payload
        payload = {
            'dashboard': dashboard_config,
            'overwrite': True,
            'message': f'Updated by MAMS monitoring service at {datetime.utcnow().isoformat()}'
        }
        
        if dashboard_uid:
            payload['dashboard']['uid'] = dashboard_uid
        
        # Create/update dashboard
        create_url = f"{self.grafana_url}/api/dashboards/db"
        response = await client.post(
            create_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Failed to create dashboard: {response.status_code} {response.text}")
    
    def _create_system_overview_dashboard(self) -> Dict[str, Any]:
        """Create system overview dashboard."""
        return {
            'title': 'MAMS - System Overview',
            'tags': ['mams', 'system', 'overview'],
            'timezone': 'browser',
            'refresh': '30s',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'panels': [
                # CPU Usage
                {
                    'id': 1,
                    'title': 'CPU Usage by Service',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'mams_cpu_usage_percent',
                            'legendFormat': '{{service}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'percent',
                            'min': 0,
                            'max': 100,
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 70},
                                    {'color': 'red', 'value': 90}
                                ]
                            }
                        }
                    }
                },
                
                # Memory Usage
                {
                    'id': 2,
                    'title': 'Memory Usage by Service',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'mams_memory_usage_bytes{type="used"}',
                            'legendFormat': '{{service}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'bytes',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 80000000000},  # 80GB
                                    {'color': 'red', 'value': 95000000000}      # 95GB
                                ]
                            }
                        }
                    }
                },
                
                # Request Rate
                {
                    'id': 3,
                    'title': 'Request Rate by Service',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(mams_requests_total[5m])',
                            'legendFormat': '{{service}} - {{endpoint}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'reqps'
                        }
                    }
                },
                
                # Error Rate
                {
                    'id': 4,
                    'title': 'Error Rate by Service',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(mams_requests_total{status=~"4..|5.."}[5m]) / rate(mams_requests_total[5m])',
                            'legendFormat': '{{service}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'percentunit',
                            'max': 1,
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 0.05},
                                    {'color': 'red', 'value': 0.10}
                                ]
                            }
                        }
                    }
                },
                
                # Active Users
                {
                    'id': 5,
                    'title': 'Active Users',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 0, 'y': 16},
                    'targets': [
                        {
                            'expr': 'mams_active_users',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 500},
                                    {'color': 'red', 'value': 1000}
                                ]
                            }
                        }
                    }
                },
                
                # Storage Usage
                {
                    'id': 6,
                    'title': 'Storage Usage',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 6, 'y': 16},
                    'targets': [
                        {
                            'expr': 'mams_storage_used_bytes',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'bytes',
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 85000000000000},  # 85TB
                                    {'color': 'red', 'value': 95000000000000}      # 95TB
                                ]
                            }
                        }
                    }
                },
                
                # Upload Queue Size
                {
                    'id': 7,
                    'title': 'Upload Queue Size',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 12, 'y': 16},
                    'targets': [
                        {
                            'expr': 'mams_upload_queue_size',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 100},
                                    {'color': 'red', 'value': 500}
                                ]
                            }
                        }
                    }
                },
                
                # Processing Queue Size
                {
                    'id': 8,
                    'title': 'Processing Queue Size',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 18, 'y': 16},
                    'targets': [
                        {
                            'expr': 'mams_processing_queue_size',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 50},
                                    {'color': 'red', 'value': 200}
                                ]
                            }
                        }
                    }
                }
            ]
        }
    
    def _create_application_performance_dashboard(self) -> Dict[str, Any]:
        """Create application performance dashboard."""
        return {
            'title': 'MAMS - Application Performance',
            'tags': ['mams', 'performance', 'application'],
            'timezone': 'browser',
            'refresh': '30s',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'panels': [
                # Response Time Percentiles
                {
                    'id': 1,
                    'title': 'Response Time Percentiles',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.50, rate(mams_request_duration_seconds_bucket[5m]))',
                            'legendFormat': 'p50',
                            'refId': 'A'
                        },
                        {
                            'expr': 'histogram_quantile(0.90, rate(mams_request_duration_seconds_bucket[5m]))',
                            'legendFormat': 'p90',
                            'refId': 'B'
                        },
                        {
                            'expr': 'histogram_quantile(0.95, rate(mams_request_duration_seconds_bucket[5m]))',
                            'legendFormat': 'p95',
                            'refId': 'C'
                        },
                        {
                            'expr': 'histogram_quantile(0.99, rate(mams_request_duration_seconds_bucket[5m]))',
                            'legendFormat': 'p99',
                            'refId': 'D'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 's',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 1},
                                    {'color': 'red', 'value': 5}
                                ]
                            }
                        }
                    }
                },
                
                # Database Query Performance
                {
                    'id': 2,
                    'title': 'Database Query Performance',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.95, rate(mams_db_query_duration_seconds_bucket[5m]))',
                            'legendFormat': '{{service}} - {{query_type}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 's',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 0.1},
                                    {'color': 'red', 'value': 1}
                                ]
                            }
                        }
                    }
                },
                
                # Cache Hit Rate
                {
                    'id': 3,
                    'title': 'Cache Hit Rate',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(mams_cache_hits_total[5m]) / (rate(mams_cache_hits_total[5m]) + rate(mams_cache_misses_total[5m]))',
                            'legendFormat': '{{service}} - {{cache_type}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'percentunit',
                            'min': 0,
                            'max': 1,
                            'thresholds': {
                                'steps': [
                                    {'color': 'red', 'value': None},
                                    {'color': 'yellow', 'value': 0.7},
                                    {'color': 'green', 'value': 0.9}
                                ]
                            }
                        }
                    }
                },
                
                # Throughput by Endpoint
                {
                    'id': 4,
                    'title': 'Throughput by Endpoint',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 8},
                    'targets': [
                        {
                            'expr': 'rate(mams_requests_total[5m])',
                            'legendFormat': '{{service}}/{{endpoint}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'reqps'
                        }
                    }
                }
            ]
        }
    
    def _create_web_vitals_dashboard(self) -> Dict[str, Any]:
        """Create Core Web Vitals dashboard."""
        return {
            'title': 'MAMS - Core Web Vitals',
            'tags': ['mams', 'frontend', 'web-vitals', 'user-experience'],
            'timezone': 'browser',
            'refresh': '1m',
            'time': {
                'from': 'now-24h',
                'to': 'now'
            },
            'panels': [
                # LCP (Largest Contentful Paint)
                {
                    'id': 1,
                    'title': 'Largest Contentful Paint (LCP)',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 8, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.75, rate(web_vitals_lcp_bucket[1h]))',
                            'legendFormat': '75th percentile',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ms',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 2500},
                                    {'color': 'red', 'value': 4000}
                                ]
                            }
                        }
                    }
                },
                
                # FID (First Input Delay)
                {
                    'id': 2,
                    'title': 'First Input Delay (FID)',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 8, 'x': 8, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.75, rate(web_vitals_fid_bucket[1h]))',
                            'legendFormat': '75th percentile',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ms',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 100},
                                    {'color': 'red', 'value': 300}
                                ]
                            }
                        }
                    }
                },
                
                # CLS (Cumulative Layout Shift)
                {
                    'id': 3,
                    'title': 'Cumulative Layout Shift (CLS)',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 8, 'x': 16, 'y': 0},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.75, rate(web_vitals_cls_bucket[1h]))',
                            'legendFormat': '75th percentile',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'short',
                            'decimals': 3,
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 0.1},
                                    {'color': 'red', 'value': 0.25}
                                ]
                            }
                        }
                    }
                },
                
                # Core Web Vitals Score Distribution
                {
                    'id': 4,
                    'title': 'Core Web Vitals Score Distribution',
                    'type': 'piechart',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 8},
                    'targets': [
                        {
                            'expr': 'sum(web_vitals_score{score="good"})',
                            'legendFormat': 'Good',
                            'refId': 'A'
                        },
                        {
                            'expr': 'sum(web_vitals_score{score="needs_improvement"})',
                            'legendFormat': 'Needs Improvement',
                            'refId': 'B'
                        },
                        {
                            'expr': 'sum(web_vitals_score{score="poor"})',
                            'legendFormat': 'Poor',
                            'refId': 'C'
                        }
                    ],
                    'options': {
                        'pieType': 'pie'
                    }
                },
                
                # Page Performance Breakdown
                {
                    'id': 5,
                    'title': 'Performance by Page',
                    'type': 'table',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 8},
                    'targets': [
                        {
                            'expr': 'histogram_quantile(0.75, rate(web_vitals_lcp_bucket[1h])) by (page)',
                            'legendFormat': '{{page}}',
                            'refId': 'A',
                            'format': 'table'
                        }
                    ],
                    'transformations': [
                        {
                            'id': 'organize',
                            'options': {
                                'excludeByName': {},
                                'indexByName': {},
                                'renameByName': {
                                    'Value': 'LCP (ms)'
                                }
                            }
                        }
                    ]
                }
            ]
        }
    
    def _create_business_metrics_dashboard(self) -> Dict[str, Any]:
        """Create business metrics dashboard."""
        return {
            'title': 'MAMS - Business Metrics',
            'tags': ['mams', 'business', 'metrics'],
            'timezone': 'browser',
            'refresh': '5m',
            'time': {
                'from': 'now-24h',
                'to': 'now'
            },
            'panels': [
                # Assets Uploaded
                {
                    'id': 1,
                    'title': 'Assets Uploaded (24h)',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'increase(mams_assets_uploaded_total[24h])',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'color': {'mode': 'palette-classic'},
                            'unit': 'short'
                        }
                    }
                },
                
                # Upload Rate by Asset Type
                {
                    'id': 2,
                    'title': 'Upload Rate by Asset Type',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 4},
                    'targets': [
                        {
                            'expr': 'rate(mams_assets_uploaded_total[5m])',
                            'legendFormat': '{{asset_type}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ops'
                        }
                    }
                },
                
                # Storage Growth
                {
                    'id': 3,
                    'title': 'Storage Growth',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 4},
                    'targets': [
                        {
                            'expr': 'mams_storage_used_bytes',
                            'legendFormat': '{{storage_type}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'bytes'
                        }
                    }
                }
            ]
        }
    
    def _create_error_monitoring_dashboard(self) -> Dict[str, Any]:
        """Create error monitoring dashboard."""
        return {
            'title': 'MAMS - Error Monitoring',
            'tags': ['mams', 'errors', 'monitoring'],
            'timezone': 'browser',
            'refresh': '30s',
            'time': {
                'from': 'now-1h',
                'to': 'now'
            },
            'panels': [
                # Error Rate by Service
                {
                    'id': 1,
                    'title': 'Error Rate by Service',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'rate(mams_errors_total[5m])',
                            'legendFormat': '{{service}} - {{severity}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ops',
                            'thresholds': {
                                'steps': [
                                    {'color': 'green', 'value': None},
                                    {'color': 'yellow', 'value': 1},
                                    {'color': 'red', 'value': 5}
                                ]
                            }
                        }
                    }
                },
                
                # HTTP Error Responses
                {
                    'id': 2,
                    'title': 'HTTP Error Responses',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 0},
                    'targets': [
                        {
                            'expr': 'rate(mams_requests_total{status=~"4..|5.."}[5m])',
                            'legendFormat': '{{service}} - {{status}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'reqps'
                        }
                    }
                }
            ]
        }
    
    def _create_user_experience_dashboard(self) -> Dict[str, Any]:
        """Create user experience dashboard."""
        return {
            'title': 'MAMS - User Experience',
            'tags': ['mams', 'user-experience', 'ux'],
            'timezone': 'browser',
            'refresh': '1m',
            'time': {
                'from': 'now-24h',
                'to': 'now'
            },
            'panels': [
                # Session Duration
                {
                    'id': 1,
                    'title': 'Average Session Duration',
                    'type': 'stat',
                    'gridPos': {'h': 4, 'w': 6, 'x': 0, 'y': 0},
                    'targets': [
                        {
                            'expr': 'avg(user_session_duration_seconds)',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'dtdurations',
                            'color': {'mode': 'thresholds'},
                            'thresholds': {
                                'steps': [
                                    {'color': 'red', 'value': None},
                                    {'color': 'yellow', 'value': 300},
                                    {'color': 'green', 'value': 900}
                                ]
                            }
                        }
                    }
                },
                
                # Page Views
                {
                    'id': 2,
                    'title': 'Page Views by Route',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 0, 'y': 4},
                    'targets': [
                        {
                            'expr': 'rate(page_views_total[5m])',
                            'legendFormat': '{{route}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ops'
                        }
                    }
                },
                
                # User Actions
                {
                    'id': 3,
                    'title': 'User Actions',
                    'type': 'timeseries',
                    'gridPos': {'h': 8, 'w': 12, 'x': 12, 'y': 4},
                    'targets': [
                        {
                            'expr': 'rate(user_actions_total[5m])',
                            'legendFormat': '{{action}}',
                            'refId': 'A'
                        }
                    ],
                    'fieldConfig': {
                        'defaults': {
                            'unit': 'ops'
                        }
                    }
                }
            ]
        }
    
    async def setup_data_sources(self) -> Dict[str, Any]:
        """Setup required data sources in Grafana."""
        data_sources = [
            {
                'name': 'Prometheus',
                'type': 'prometheus',
                'url': 'http://prometheus:9090',
                'access': 'proxy',
                'isDefault': True
            },
            {
                'name': 'Redis',
                'type': 'redis-datasource',
                'url': 'redis://redis:6379',
                'access': 'proxy'
            }
        ]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            for ds_config in data_sources:
                try:
                    # Check if data source exists
                    get_url = f"{self.grafana_url}/api/datasources/name/{ds_config['name']}"
                    response = await client.get(get_url, headers=self.headers)
                    
                    if response.status_code == 404:
                        # Create new data source
                        create_url = f"{self.grafana_url}/api/datasources"
                        response = await client.post(
                            create_url,
                            headers=self.headers,
                            json=ds_config
                        )
                    
                    results[ds_config['name']] = {
                        'status': 'success' if response.status_code in [200, 201] else 'error',
                        'message': response.text
                    }
                    
                except Exception as e:
                    results[ds_config['name']] = {
                        'status': 'error',
                        'message': str(e)
                    }
        
        return results


# CLI interface for dashboard management
async def main():
    """Main function for dashboard management."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Manage MAMS Grafana dashboards')
    parser.add_argument('--grafana-url', required=True, help='Grafana URL')
    parser.add_argument('--api-key', required=True, help='Grafana API key')
    parser.add_argument('--action', choices=['create', 'update', 'setup-datasources'], 
                       default='create', help='Action to perform')
    
    args = parser.parse_args()
    
    manager = GrafanaDashboardManager(args.grafana_url, args.api_key)
    
    if args.action == 'setup-datasources':
        print("Setting up data sources...")
        results = await manager.setup_data_sources()
        print(json.dumps(results, indent=2))
    
    elif args.action in ['create', 'update']:
        print("Creating/updating dashboards...")
        results = await manager.create_all_dashboards()
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())