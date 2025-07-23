"""
OpenSearch database connection and index management
"""

import json
import ssl
from typing import Dict, Any, Optional, List
from functools import lru_cache
import structlog
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
from opensearchpy.exceptions import RequestError, NotFoundError

from ..core.config import get_settings
from ..core.exceptions import (
    ConnectionError, IndexError, IndexNotFoundError, 
    IndexAlreadyExistsError, ConfigurationError
)

logger = structlog.get_logger()

# Global client instance
_opensearch_client: Optional[AsyncOpenSearch] = None


async def get_opensearch_client() -> AsyncOpenSearch:
    """Get or create OpenSearch client instance"""
    global _opensearch_client
    
    if _opensearch_client is None:
        _opensearch_client = await create_opensearch_client()
    
    return _opensearch_client


async def create_opensearch_client() -> AsyncOpenSearch:
    """Create new OpenSearch client"""
    settings = get_settings()
    
    try:
        # Configure SSL context if needed
        ssl_context = None
        if settings.opensearch_scheme == "https":
            ssl_context = ssl.create_default_context()
            if not settings.opensearch_ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            elif settings.opensearch_ssl_cert_path:
                ssl_context.load_verify_locations(settings.opensearch_ssl_cert_path)
        
        # Create client configuration
        client_config = {
            "hosts": [{"host": settings.opensearch_host, "port": settings.opensearch_port}],
            "connection_class": RequestsHttpConnection,
            "timeout": settings.opensearch_timeout,
            "max_retries": settings.opensearch_max_retries,
            "retry_on_timeout": True,
            "use_ssl": settings.opensearch_scheme == "https",
            "verify_certs": settings.opensearch_ssl_verify,
        }
        
        # Add authentication if configured
        if settings.opensearch_auth:
            client_config["http_auth"] = settings.opensearch_auth
        
        # Add SSL context if configured
        if ssl_context:
            client_config["ssl_context"] = ssl_context
        
        # Create client
        client = AsyncOpenSearch(**client_config)
        
        # Test connection
        await client.cluster.health()
        
        logger.info(
            "opensearch_connection_established",
            host=settings.opensearch_host,
            port=settings.opensearch_port,
            scheme=settings.opensearch_scheme
        )
        
        return client
        
    except OpenSearchConnectionError as e:
        logger.error("opensearch_connection_failed", error=str(e))
        raise ConnectionError(
            f"Failed to connect to OpenSearch at {settings.opensearch_url}",
            host=settings.opensearch_url
        )
    except Exception as e:
        logger.error("opensearch_client_creation_failed", error=str(e))
        raise ConfigurationError(f"Failed to create OpenSearch client: {str(e)}")


async def close_opensearch_client():
    """Close OpenSearch client connection"""
    global _opensearch_client
    
    if _opensearch_client:
        await _opensearch_client.close()
        _opensearch_client = None
        logger.info("opensearch_connection_closed")


class IndexManager:
    """Manages OpenSearch indices for MAMS"""
    
    def __init__(self, client: AsyncOpenSearch):
        self.client = client
        self.settings = get_settings()
    
    async def initialize_indices(self):
        """Initialize all required indices"""
        indices = [
            (self.settings.assets_index_name, self._get_assets_index_config()),
            (self.settings.metadata_index_name, self._get_metadata_index_config()),
            (self.settings.content_index_name, self._get_content_index_config()),
            (self.settings.logs_index_name, self._get_logs_index_config()),
        ]
        
        for index_name, index_config in indices:
            await self.create_index_if_not_exists(index_name, index_config)
    
    async def create_index_if_not_exists(self, index_name: str, index_config: Dict[str, Any]):
        """Create index if it doesn't exist"""
        try:
            exists = await self.client.indices.exists(index=index_name)
            
            if not exists:
                await self.create_index(index_name, index_config)
                logger.info("index_created", index_name=index_name)
            else:
                logger.info("index_already_exists", index_name=index_name)
                
        except Exception as e:
            logger.error("index_creation_check_failed", index_name=index_name, error=str(e))
            raise IndexError(f"Failed to check/create index {index_name}: {str(e)}", index_name)
    
    async def create_index(self, index_name: str, index_config: Dict[str, Any]):
        """Create a new index"""
        try:
            response = await self.client.indices.create(
                index=index_name,
                body=index_config
            )
            
            logger.info(
                "index_created_successfully",
                index_name=index_name,
                acknowledged=response.get("acknowledged", False)
            )
            
            return response
            
        except RequestError as e:
            if "resource_already_exists_exception" in str(e):
                raise IndexAlreadyExistsError(index_name)
            else:
                raise IndexError(f"Failed to create index {index_name}: {str(e)}", index_name)
        except Exception as e:
            raise IndexError(f"Unexpected error creating index {index_name}: {str(e)}", index_name)
    
    async def delete_index(self, index_name: str):
        """Delete an index"""
        try:
            response = await self.client.indices.delete(index=index_name)
            logger.info("index_deleted", index_name=index_name)
            return response
            
        except NotFoundError:
            raise IndexNotFoundError(index_name)
        except Exception as e:
            raise IndexError(f"Failed to delete index {index_name}: {str(e)}", index_name)
    
    async def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """Get index information"""
        try:
            response = await self.client.indices.get(index=index_name)
            return response
            
        except NotFoundError:
            raise IndexNotFoundError(index_name)
        except Exception as e:
            raise IndexError(f"Failed to get index info for {index_name}: {str(e)}", index_name)
    
    async def refresh_index(self, index_name: str):
        """Refresh an index"""
        try:
            response = await self.client.indices.refresh(index=index_name)
            logger.info("index_refreshed", index_name=index_name)
            return response
            
        except NotFoundError:
            raise IndexNotFoundError(index_name)
        except Exception as e:
            raise IndexError(f"Failed to refresh index {index_name}: {str(e)}", index_name)
    
    def _get_assets_index_config(self) -> Dict[str, Any]:
        """Get configuration for assets index"""
        return {
            "settings": {
                "number_of_shards": self.settings.number_of_shards,
                "number_of_replicas": self.settings.number_of_replicas,
                "refresh_interval": self.settings.refresh_interval,
                "analysis": {
                    "analyzer": {
                        "asset_name_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        },
                        "path_analyzer": {
                            "type": "custom",
                            "tokenizer": "path_hierarchy",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "asset_id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "asset_name_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "file_path": {
                        "type": "text",
                        "analyzer": "path_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "file_name": {
                        "type": "text",
                        "analyzer": "asset_name_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "file_extension": {"type": "keyword"},
                    "file_size": {"type": "long"},
                    "mime_type": {"type": "keyword"},
                    "asset_type": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "project_id": {"type": "keyword"},
                    "created_by": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "checksum": {"type": "keyword"},
                    "version": {"type": "integer"},
                    "parent_asset_id": {"type": "keyword"},
                    "storage_location": {"type": "keyword"},
                    "is_proxy": {"type": "boolean"},
                    "proxy_type": {"type": "keyword"},
                    "original_asset_id": {"type": "keyword"}
                }
            }
        }
    
    def _get_metadata_index_config(self) -> Dict[str, Any]:
        """Get configuration for metadata index"""
        return {
            "settings": {
                "number_of_shards": self.settings.number_of_shards,
                "number_of_replicas": self.settings.number_of_replicas,
                "refresh_interval": self.settings.refresh_interval,
                "analysis": {
                    "analyzer": {
                        "metadata_text_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "stop"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "asset_id": {"type": "keyword"},
                    "metadata_id": {"type": "keyword"},
                    "schema_id": {"type": "keyword"},
                    "schema_name": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "metadata_text_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "metadata_text_analyzer"
                    },
                    "keywords": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "custom_fields": {"type": "object", "dynamic": True},
                    "technical_metadata": {
                        "properties": {
                            "duration": {"type": "float"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"},
                            "bitrate": {"type": "integer"},
                            "frame_rate": {"type": "float"},
                            "codec": {"type": "keyword"},
                            "sample_rate": {"type": "integer"},
                            "channels": {"type": "integer"}
                        }
                    },
                    "extracted_text": {
                        "type": "text",
                        "analyzer": "metadata_text_analyzer"
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "version": {"type": "integer"}
                }
            }
        }
    
    def _get_content_index_config(self) -> Dict[str, Any]:
        """Get configuration for content index (for full-text search)"""
        return {
            "settings": {
                "number_of_shards": self.settings.number_of_shards,
                "number_of_replicas": self.settings.number_of_replicas,
                "refresh_interval": self.settings.refresh_interval,
                "analysis": {
                    "analyzer": {
                        "content_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "stop", "snowball"]
                        },
                        "exact_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "asset_id": {"type": "keyword"},
                    "content_id": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "content_analyzer",
                        "fields": {
                            "exact": {"type": "text", "analyzer": "exact_analyzer"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "transcript": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "ocr_text": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "subtitle_text": {
                        "type": "text",
                        "analyzer": "content_analyzer"
                    },
                    "language": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }
    
    def _get_logs_index_config(self) -> Dict[str, Any]:
        """Get configuration for search logs index"""
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "30s"
            },
            "mappings": {
                "properties": {
                    "query": {"type": "text"},
                    "filters": {"type": "object"},
                    "results_count": {"type": "integer"},
                    "response_time_ms": {"type": "integer"},
                    "user_id": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "ip_address": {"type": "ip"},
                    "user_agent": {"type": "text"},
                    "timestamp": {"type": "date"},
                    "result_clicked": {"type": "boolean"},
                    "clicked_asset_id": {"type": "keyword"},
                    "click_position": {"type": "integer"}
                }
            }
        }


async def initialize_indices(client: Optional[AsyncOpenSearch] = None):
    """Initialize all OpenSearch indices"""
    if client is None:
        client = await get_opensearch_client()
    
    index_manager = IndexManager(client)
    await index_manager.initialize_indices()
    
    logger.info("opensearch_indices_initialized")


async def get_index_manager() -> IndexManager:
    """Get index manager instance"""
    client = await get_opensearch_client()
    return IndexManager(client)