"""
Log Formatters and Output Handlers

Provides various log formatting options for different outputs
(console, file, external systems).
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
import socket


class CompactJSONFormatter(logging.Formatter):
    """Compact JSON formatter for production logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add essential fields only
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, separators=(',', ':'))


class ElasticsearchFormatter(logging.Formatter):
    """Formatter for Elasticsearch/OpenSearch ingestion"""
    
    def __init__(self, index_name: str = "api-gateway", doc_type: str = "_doc"):
        super().__init__()
        self.index_name = index_name
        self.doc_type = doc_type
        self.hostname = socket.gethostname()
    
    def format(self, record: logging.LogRecord) -> str:
        # Create document for Elasticsearch
        doc = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "host": {
                "name": self.hostname
            },
            "log": {
                "level": record.levelname,
                "logger": record.name,
                "origin": {
                    "file": {
                        "name": record.pathname,
                        "line": record.lineno
                    },
                    "function": record.funcName
                }
            },
            "message": record.getMessage(),
            "service": {
                "name": "api-gateway",
                "type": "gateway"
            },
            "event": {
                "dataset": "api-gateway.log",
                "module": "api-gateway"
            }
        }
        
        # Add custom fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                if key == 'request_id':
                    doc['trace'] = {'id': value}
                elif key == 'correlation_id':
                    doc['transaction'] = {'id': value}
                elif key == 'user_id':
                    doc['user'] = {'id': value}
                elif key == 'http_request':
                    doc['http'] = value
                else:
                    doc[key] = value
        
        # Add exception details
        if record.exc_info:
            doc['error'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stack_trace': self.formatException(record.exc_info)
            }
        
        # Format for bulk indexing
        action = {
            "index": {
                "_index": f"{self.index_name}-{datetime.utcnow().strftime('%Y.%m.%d')}",
                "_type": self.doc_type
            }
        }
        
        return json.dumps(action) + '\n' + json.dumps(doc)


class CloudWatchFormatter(logging.Formatter):
    """Formatter for AWS CloudWatch Logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # CloudWatch expects simple JSON
        log_data = {
            "timestamp": int(record.created * 1000),  # Milliseconds
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "requestId": getattr(record, 'request_id', None),
            "correlationId": getattr(record, 'correlation_id', None),
            "userId": getattr(record, 'user_id', None)
        }
        
        # Add metrics if present
        if hasattr(record, 'metric_name'):
            log_data['_aws'] = {
                'CloudWatchMetrics': [{
                    'Namespace': 'MAMS/APIGateway',
                    'Dimensions': [['Service', 'Method']],
                    'Metrics': [{
                        'Name': record.metric_name,
                        'Value': record.metric_value
                    }]
                }]
            }
        
        if record.exc_info:
            log_data['error'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1])
            }
        
        return json.dumps(log_data)


class DatadogFormatter(logging.Formatter):
    """Formatter for Datadog Log Management"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Datadog expects specific field names
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": {"name": record.name},
            "message": record.getMessage(),
            "dd": {
                "service": "api-gateway",
                "env": "production",
                "version": "1.0.0"
            }
        }
        
        # Add trace information
        if hasattr(record, 'request_id'):
            log_data['dd']['trace_id'] = record.request_id
        
        if hasattr(record, 'correlation_id'):
            log_data['dd']['span_id'] = record.correlation_id
        
        # Add user context
        if hasattr(record, 'user_id'):
            log_data['usr'] = {'id': record.user_id}
        
        # Add custom attributes
        attributes = {}
        for key, value in record.__dict__.items():
            if key.startswith('dd_') or key.startswith('attr_'):
                attributes[key] = value
        
        if attributes:
            log_data['attributes'] = attributes
        
        # Add error details
        if record.exc_info:
            log_data['error'] = {
                'kind': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stack': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Format level with color
        if self.use_colors:
            level = f"{self.COLORS.get(record.levelname, '')}{record.levelname:8}{self.RESET}"
        else:
            level = f"{record.levelname:8}"
        
        # Format logger name (truncate if too long)
        logger_name = record.name
        if len(logger_name) > 30:
            logger_name = '...' + logger_name[-27:]
        
        # Base message
        message = f"{timestamp} | {level} | {logger_name:30} | {record.getMessage()}"
        
        # Add context fields
        context_parts = []
        
        if hasattr(record, 'request_id'):
            context_parts.append(f"req_id={record.request_id[:8]}")
        
        if hasattr(record, 'user_id'):
            context_parts.append(f"user={record.user_id}")
        
        if hasattr(record, 'method') and hasattr(record, 'path'):
            context_parts.append(f"{record.method} {record.path}")
        
        if hasattr(record, 'status_code'):
            context_parts.append(f"status={record.status_code}")
        
        if hasattr(record, 'response_time'):
            context_parts.append(f"time={record.response_time:.3f}s")
        
        if context_parts:
            message += f" | {' | '.join(context_parts)}"
        
        # Add exception if present
        if record.exc_info:
            message += f"\n{''.join(traceback.format_exception(*record.exc_info))}"
        
        return message


class LogstashFormatter(logging.Formatter):
    """Formatter for Logstash ingestion"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Logstash expects @fields
        log_data = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "@version": "1",
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "source_host": socket.gethostname(),
            "fields": {
                "service": "api-gateway",
                "environment": "production"
            }
        }
        
        # Add all custom fields to @fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data['fields'][key] = value
        
        # Add exception
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'stacktrace': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)


def get_formatter(formatter_type: str, **kwargs) -> logging.Formatter:
    """Get a formatter by type"""
    formatters = {
        'compact_json': CompactJSONFormatter,
        'elasticsearch': ElasticsearchFormatter,
        'cloudwatch': CloudWatchFormatter,
        'datadog': DatadogFormatter,
        'human': HumanReadableFormatter,
        'logstash': LogstashFormatter
    }
    
    formatter_class = formatters.get(formatter_type, CompactJSONFormatter)
    return formatter_class(**kwargs)