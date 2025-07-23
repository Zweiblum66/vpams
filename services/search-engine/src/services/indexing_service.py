"""
Indexing Service - Document indexing and management
"""

import json
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import structlog
from opensearchpy import AsyncOpenSearch, helpers
from opensearchpy.exceptions import NotFoundError, RequestError, ConflictError

from ..models.schemas import (
    IndexDocument, BulkIndexRequest, IndexingResponse, 
    BulkIndexingResponse, DeleteResponse, IndexStats, IndexType
)
from ..db.opensearch import get_opensearch_client, get_index_manager
from ..core.config import get_settings
from ..core.exceptions import (
    IndexError, IndexNotFoundError, IndexingError, 
    BulkIndexingError, ValidationError
)

logger = structlog.get_logger()


class IndexingService:
    """Service for handling document indexing operations"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.settings = get_settings()
        self.index_mappings = {
            IndexType.ASSETS: self.settings.assets_index_name,
            IndexType.METADATA: self.settings.metadata_index_name,
            IndexType.CONTENT: self.settings.content_index_name,
            "logs": self.settings.logs_index_name
        }
    
    async def index_document(self, document: IndexDocument) -> IndexingResponse:
        """
        Index a single document
        
        Args:
            document: Document to index with id, document data, and optional index name
            
        Returns:
            IndexingResponse with operation details
        """
        try:
            start_time = time.time()
            
            # Determine target index
            index_name = document.index_name or self._auto_detect_index(document.document)
            
            # Validate document
            self._validate_document(document.document, index_name)
            
            # Prepare document for indexing
            processed_doc = self._prepare_document(document.document, index_name)
            
            # Index the document
            response = await self.client.index(
                index=index_name,
                id=document.id,
                body=processed_doc,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                "document_indexed_successfully",
                document_id=document.id,
                index_name=index_name,
                result=response.get("result", "unknown"),
                processing_time_ms=processing_time
            )
            
            return IndexingResponse(
                success=True,
                document_id=document.id,
                index_name=index_name,
                version=response.get("_version"),
                result=response.get("result", "created")
            )
            
        except RequestError as e:
            logger.error("document_indexing_request_error", document_id=document.id, error=str(e))
            raise IndexingError(
                f"Invalid request for document {document.id}: {str(e)}",
                document_id=document.id
            )
        except Exception as e:
            logger.error("document_indexing_failed", document_id=document.id, error=str(e))
            raise IndexingError(
                f"Failed to index document {document.id}: {str(e)}",
                document_id=document.id
            )
    
    async def bulk_index_documents(self, request: BulkIndexRequest) -> BulkIndexingResponse:
        """
        Index multiple documents in bulk
        
        Args:
            request: Bulk indexing request with documents and options
            
        Returns:
            BulkIndexingResponse with operation summary
        """
        try:
            start_time = time.time()
            total_docs = len(request.documents)
            
            logger.info("bulk_indexing_started", document_count=total_docs)
            
            # Prepare bulk actions
            actions = []
            for doc in request.documents:
                index_name = doc.index_name or self._auto_detect_index(doc.document)
                
                # Validate and prepare document
                try:
                    self._validate_document(doc.document, index_name)
                    processed_doc = self._prepare_document(doc.document, index_name)
                    
                    action = {
                        "_op_type": "index",
                        "_index": index_name,
                        "_id": doc.id,
                        "_source": processed_doc
                    }
                    actions.append(action)
                    
                except Exception as e:
                    logger.warning(
                        "document_preparation_failed",
                        document_id=doc.id,
                        error=str(e)
                    )
                    # Continue with other documents
                    continue
            
            if not actions:
                raise BulkIndexingError("No valid documents to index")
            
            # Execute bulk operation
            success_count = 0
            failed_count = 0
            errors = []
            
            try:
                # Use helpers.async_bulk for efficient bulk operations
                async for success, info in helpers.async_bulk(
                    self.client,
                    actions,
                    chunk_size=self.settings.bulk_index_size,
                    max_retries=3,
                    initial_backoff=2,
                    max_backoff=600
                ):
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(info)
                        logger.warning("bulk_document_failed", error=info)
                        
            except Exception as e:
                logger.error("bulk_operation_failed", error=str(e))
                raise BulkIndexingError(f"Bulk operation failed: {str(e)}")
            
            # Refresh indices if requested
            if request.refresh:
                try:
                    indices_to_refresh = set(
                        doc.index_name or self._auto_detect_index(doc.document) 
                        for doc in request.documents
                    )
                    for index_name in indices_to_refresh:
                        await self.refresh_index(index_name)
                except Exception as e:
                    logger.warning("bulk_refresh_failed", error=str(e))
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                "bulk_indexing_completed",
                total_documents=total_docs,
                successful_count=success_count,
                failed_count=failed_count,
                processing_time_ms=processing_time
            )
            
            return BulkIndexingResponse(
                success=failed_count == 0,
                total_documents=total_docs,
                successful_count=success_count,
                failed_count=failed_count,
                errors=errors,
                took=processing_time
            )
            
        except BulkIndexingError:
            raise
        except Exception as e:
            logger.error("bulk_indexing_error", error=str(e))
            raise BulkIndexingError(f"Bulk indexing operation failed: {str(e)}")
    
    async def delete_document(self, index_name: str, document_id: str) -> DeleteResponse:
        """
        Delete a document from an index
        
        Args:
            index_name: Name of the index
            document_id: ID of the document to delete
            
        Returns:
            DeleteResponse with operation details
        """
        try:
            logger.info("document_deletion_started", index_name=index_name, document_id=document_id)
            
            response = await self.client.delete(
                index=index_name,
                id=document_id,
                timeout=f"{self.settings.search_timeout}s"
            )
            
            logger.info(
                "document_deleted_successfully",
                index_name=index_name,
                document_id=document_id,
                result=response.get("result", "unknown")
            )
            
            return DeleteResponse(
                success=True,
                document_id=document_id,
                index_name=index_name,
                result=response.get("result", "deleted")
            )
            
        except NotFoundError:
            logger.warning("document_not_found_for_deletion", index_name=index_name, document_id=document_id)
            raise IndexingError(
                f"Document {document_id} not found in index {index_name}",
                document_id=document_id
            )
        except Exception as e:
            logger.error("document_deletion_failed", index_name=index_name, document_id=document_id, error=str(e))
            raise IndexingError(
                f"Failed to delete document {document_id} from index {index_name}: {str(e)}",
                document_id=document_id
            )
    
    async def get_indices_stats(self) -> List[IndexStats]:
        """
        Get statistics for all MAMS indices
        
        Returns:
            List of IndexStats for each index
        """
        try:
            stats = []
            
            # Get stats for all MAMS indices
            for index_type, index_name in self.index_mappings.items():
                try:
                    index_stats = await self.get_index_stats(index_name)
                    stats.append(index_stats)
                except IndexNotFoundError:
                    # Index doesn't exist yet, skip it
                    logger.debug("index_not_found_in_stats", index_name=index_name)
                    continue
                except Exception as e:
                    logger.warning("index_stats_failed", index_name=index_name, error=str(e))
                    continue
            
            logger.info("indices_stats_retrieved", index_count=len(stats))
            return stats
            
        except Exception as e:
            logger.error("indices_stats_error", error=str(e))
            raise IndexError(f"Failed to get indices statistics: {str(e)}")
    
    async def get_index_stats(self, index_name: str) -> IndexStats:
        """
        Get statistics for a specific index
        
        Args:
            index_name: Name of the index
            
        Returns:
            IndexStats for the specified index
        """
        try:
            # Get index stats
            stats_response = await self.client.indices.stats(index=index_name)
            
            if index_name not in stats_response.get("indices", {}):
                raise IndexNotFoundError(index_name)
            
            index_data = stats_response["indices"][index_name]
            
            # Get index settings for shard information
            settings_response = await self.client.indices.get_settings(index=index_name)
            settings = settings_response[index_name]["settings"]["index"]
            
            # Get index health
            health_response = await self.client.cluster.health(index=index_name)
            
            return IndexStats(
                index_name=index_name,
                document_count=index_data["total"]["docs"]["count"],
                store_size=self._format_bytes(index_data["total"]["store"]["size_in_bytes"]),
                primary_shards=int(settings.get("number_of_shards", 1)),
                replica_shards=int(settings.get("number_of_replicas", 0)),
                status=health_response.get("status", "unknown")
            )
            
        except NotFoundError:
            raise IndexNotFoundError(index_name)
        except Exception as e:
            logger.error("index_stats_failed", index_name=index_name, error=str(e))
            raise IndexError(f"Failed to get stats for index {index_name}: {str(e)}", index_name)
    
    async def refresh_index(self, index_name: str):
        """
        Refresh an index to make recent changes searchable
        
        Args:
            index_name: Name of the index to refresh
        """
        try:
            index_manager = await get_index_manager()
            await index_manager.refresh_index(index_name)
            
            logger.info("index_refreshed_by_service", index_name=index_name)
            
        except IndexNotFoundError:
            raise
        except Exception as e:
            logger.error("index_refresh_failed", index_name=index_name, error=str(e))
            raise IndexError(f"Failed to refresh index {index_name}: {str(e)}", index_name)
    
    def _auto_detect_index(self, document: Dict[str, Any]) -> str:
        """
        Auto-detect the appropriate index for a document based on its content
        
        Args:
            document: Document data
            
        Returns:
            Index name
        """
        # Check for asset-specific fields
        if any(field in document for field in ["asset_id", "file_path", "file_name", "mime_type"]):
            return self.settings.assets_index_name
        
        # Check for metadata-specific fields
        if any(field in document for field in ["metadata_id", "schema_id", "custom_fields"]):
            return self.settings.metadata_index_name
        
        # Check for content-specific fields
        if any(field in document for field in ["content", "transcript", "ocr_text"]):
            return self.settings.content_index_name
        
        # Default to assets index
        return self.settings.assets_index_name
    
    def _validate_document(self, document: Dict[str, Any], index_name: str):
        """
        Validate document before indexing
        
        Args:
            document: Document data
            index_name: Target index name
            
        Raises:
            ValidationError: If document is invalid
        """
        if not document:
            raise ValidationError("Document cannot be empty")
        
        # Check for required fields based on index type
        if index_name == self.settings.assets_index_name:
            if "asset_id" not in document:
                raise ValidationError("Asset documents must have an 'asset_id' field")
        
        elif index_name == self.settings.metadata_index_name:
            if "asset_id" not in document:
                raise ValidationError("Metadata documents must have an 'asset_id' field")
        
        elif index_name == self.settings.content_index_name:
            if "asset_id" not in document:
                raise ValidationError("Content documents must have an 'asset_id' field")
        
        # Validate document size (prevent very large documents)
        doc_size = len(json.dumps(document).encode('utf-8'))
        max_size = 10 * 1024 * 1024  # 10MB limit
        if doc_size > max_size:
            raise ValidationError(f"Document too large: {doc_size} bytes (max: {max_size})")
    
    def _prepare_document(self, document: Dict[str, Any], index_name: str) -> Dict[str, Any]:
        """
        Prepare document for indexing by adding metadata and transforming fields
        
        Args:
            document: Original document data
            index_name: Target index name
            
        Returns:
            Processed document ready for indexing
        """
        processed_doc = document.copy()
        
        # Add indexing metadata
        now = datetime.utcnow().isoformat()
        processed_doc.update({
            "indexed_at": now,
            "index_name": index_name,
            "document_version": 1
        })
        
        # Index-specific processing
        if index_name == self.settings.assets_index_name:
            processed_doc = self._prepare_asset_document(processed_doc)
        elif index_name == self.settings.metadata_index_name:
            processed_doc = self._prepare_metadata_document(processed_doc)
        elif index_name == self.settings.content_index_name:
            processed_doc = self._prepare_content_document(processed_doc)
        
        return processed_doc
    
    def _prepare_asset_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare asset document for indexing"""
        # Ensure consistent field types
        if "file_size" in document:
            try:
                document["file_size"] = int(document["file_size"])
            except (ValueError, TypeError):
                document["file_size"] = 0
        
        if "tags" in document and isinstance(document["tags"], str):
            document["tags"] = [tag.strip() for tag in document["tags"].split(",") if tag.strip()]
        
        # Add search-friendly fields
        if "file_path" in document:
            document["file_path_normalized"] = document["file_path"].lower()
        
        # Add suggestion data for auto-completion
        if "name" in document and isinstance(document["name"], str):
            name_value = document["name"]
            # Create suggestion input with the full name and individual words
            suggestion_inputs = [name_value]
            # Add individual words for partial matching
            words = name_value.split()
            if len(words) > 1:
                suggestion_inputs.extend(words)
            
            # Store name as string (OpenSearch will handle the mapping)
            # The mapping defines name.suggest as a completion field
            document["name"] = name_value
        
        return document
    
    def _prepare_metadata_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare metadata document for indexing"""
        # Flatten custom fields for easier searching
        if "custom_fields" in document and isinstance(document["custom_fields"], dict):
            for key, value in document["custom_fields"].items():
                if isinstance(value, (str, int, float, bool)):
                    document[f"custom_{key}"] = value
        
        return document
    
    def _prepare_content_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content document for indexing"""
        # Combine all text content for full-text search
        text_fields = ["content", "transcript", "ocr_text", "subtitle_text"]
        all_text = []
        
        for field in text_fields:
            if field in document and document[field]:
                all_text.append(str(document[field]))
        
        if all_text:
            document["all_text"] = " ".join(all_text)
        
        return document
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"


async def get_indexing_service() -> IndexingService:
    """Get indexing service instance"""
    client = await get_opensearch_client()
    return IndexingService(client)