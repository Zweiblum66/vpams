"""
Data Pipeline Service - Handles data flow from other services to search indices
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import structlog
from opensearchpy import AsyncOpenSearch

from ..models.schemas import IndexDocument, BulkIndexRequest
from ..services.indexing_service import IndexingService, get_indexing_service
from ..core.config import get_settings
from ..core.exceptions import IndexingError

logger = structlog.get_logger()


class DataPipeline:
    """Service for handling data pipeline operations"""
    
    def __init__(self, indexing_service: IndexingService):
        self.indexing_service = indexing_service
        self.settings = get_settings()
        self.transform_functions = {
            "asset": self._transform_asset_data,
            "metadata": self._transform_metadata_data,
            "content": self._transform_content_data
        }
    
    async def process_asset_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process asset creation/update event
        
        Args:
            event_data: Asset event data from asset-management service
            
        Returns:
            Success status
        """
        try:
            logger.info("processing_asset_event", asset_id=event_data.get("asset_id"))
            
            # Transform asset data for search indexing
            search_document = self._transform_asset_data(event_data)
            
            # Create index document
            index_doc = IndexDocument(
                id=event_data["asset_id"],
                document=search_document,
                index_name=self.settings.assets_index_name
            )
            
            # Index the document
            result = await self.indexing_service.index_document(index_doc)
            
            logger.info(
                "asset_event_processed",
                asset_id=event_data.get("asset_id"),
                success=result.success
            )
            
            return result.success
            
        except Exception as e:
            logger.error(
                "asset_event_processing_failed",
                asset_id=event_data.get("asset_id"),
                error=str(e)
            )
            return False
    
    async def process_metadata_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process metadata creation/update event
        
        Args:
            event_data: Metadata event data from metadata service
            
        Returns:
            Success status
        """
        try:
            logger.info("processing_metadata_event", asset_id=event_data.get("asset_id"))
            
            # Transform metadata for search indexing
            search_document = self._transform_metadata_data(event_data)
            
            # Create index document
            index_doc = IndexDocument(
                id=f"{event_data['asset_id']}_metadata",
                document=search_document,
                index_name=self.settings.metadata_index_name
            )
            
            # Index the document
            result = await self.indexing_service.index_document(index_doc)
            
            logger.info(
                "metadata_event_processed",
                asset_id=event_data.get("asset_id"),
                success=result.success
            )
            
            return result.success
            
        except Exception as e:
            logger.error(
                "metadata_event_processing_failed",
                asset_id=event_data.get("asset_id"),
                error=str(e)
            )
            return False
    
    async def process_content_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process content extraction event (transcripts, OCR, etc.)
        
        Args:
            event_data: Content event data from AI/ML service
            
        Returns:
            Success status
        """
        try:
            logger.info("processing_content_event", asset_id=event_data.get("asset_id"))
            
            # Transform content data for search indexing
            search_document = self._transform_content_data(event_data)
            
            # Create index document
            index_doc = IndexDocument(
                id=f"{event_data['asset_id']}_content",
                document=search_document,
                index_name=self.settings.content_index_name
            )
            
            # Index the document
            result = await self.indexing_service.index_document(index_doc)
            
            logger.info(
                "content_event_processed",
                asset_id=event_data.get("asset_id"),
                success=result.success
            )
            
            return result.success
            
        except Exception as e:
            logger.error(
                "content_event_processing_failed",
                asset_id=event_data.get("asset_id"),
                error=str(e)
            )
            return False
    
    async def process_bulk_data(self, data_items: List[Dict[str, Any]], data_type: str) -> Dict[str, Any]:
        """
        Process multiple data items in bulk
        
        Args:
            data_items: List of data items to process
            data_type: Type of data (asset, metadata, content)
            
        Returns:
            Processing results summary
        """
        try:
            logger.info("processing_bulk_data", count=len(data_items), data_type=data_type)
            
            # Get transform function for data type
            transform_func = self.transform_functions.get(data_type)
            if not transform_func:
                raise ValueError(f"Unknown data type: {data_type}")
            
            # Prepare documents for bulk indexing
            documents = []
            for item in data_items:
                try:
                    search_document = transform_func(item)
                    
                    # Determine document ID and index based on data type
                    if data_type == "asset":
                        doc_id = item["asset_id"]
                        index_name = self.settings.assets_index_name
                    elif data_type == "metadata":
                        doc_id = f"{item['asset_id']}_metadata"
                        index_name = self.settings.metadata_index_name
                    elif data_type == "content":
                        doc_id = f"{item['asset_id']}_content"
                        index_name = self.settings.content_index_name
                    
                    index_doc = IndexDocument(
                        id=doc_id,
                        document=search_document,
                        index_name=index_name
                    )
                    documents.append(index_doc)
                    
                except Exception as e:
                    logger.warning(
                        "bulk_item_preparation_failed",
                        item_id=item.get("asset_id"),
                        error=str(e)
                    )
                    continue
            
            if not documents:
                return {
                    "success": False,
                    "message": "No valid documents to process",
                    "processed_count": 0,
                    "failed_count": len(data_items)
                }
            
            # Execute bulk indexing
            bulk_request = BulkIndexRequest(documents=documents, refresh=True)
            result = await self.indexing_service.bulk_index_documents(bulk_request)
            
            logger.info(
                "bulk_data_processed",
                data_type=data_type,
                total_items=len(data_items),
                successful_count=result.successful_count,
                failed_count=result.failed_count
            )
            
            return {
                "success": result.success,
                "total_items": len(data_items),
                "processed_count": result.successful_count,
                "failed_count": result.failed_count,
                "processing_time_ms": result.took,
                "errors": result.errors
            }
            
        except Exception as e:
            logger.error("bulk_data_processing_failed", data_type=data_type, error=str(e))
            return {
                "success": False,
                "message": str(e),
                "processed_count": 0,
                "failed_count": len(data_items)
            }
    
    async def delete_asset_data(self, asset_id: str) -> Dict[str, bool]:
        """
        Delete all data related to an asset from search indices
        
        Args:
            asset_id: Asset ID to delete
            
        Returns:
            Dictionary with deletion results for each index
        """
        results = {}
        
        # Delete from assets index
        try:
            await self.indexing_service.delete_document(
                self.settings.assets_index_name,
                asset_id
            )
            results["assets"] = True
            logger.info("asset_deleted_from_assets_index", asset_id=asset_id)
        except Exception as e:
            results["assets"] = False
            logger.warning("asset_deletion_failed_assets_index", asset_id=asset_id, error=str(e))
        
        # Delete from metadata index
        try:
            await self.indexing_service.delete_document(
                self.settings.metadata_index_name,
                f"{asset_id}_metadata"
            )
            results["metadata"] = True
            logger.info("asset_deleted_from_metadata_index", asset_id=asset_id)
        except Exception as e:
            results["metadata"] = False
            logger.warning("asset_deletion_failed_metadata_index", asset_id=asset_id, error=str(e))
        
        # Delete from content index
        try:
            await self.indexing_service.delete_document(
                self.settings.content_index_name,
                f"{asset_id}_content"
            )
            results["content"] = True
            logger.info("asset_deleted_from_content_index", asset_id=asset_id)
        except Exception as e:
            results["content"] = False
            logger.warning("asset_deletion_failed_content_index", asset_id=asset_id, error=str(e))
        
        return results
    
    def _transform_asset_data(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform asset data for search indexing"""
        return {
            "asset_id": asset_data.get("asset_id"),
            "name": asset_data.get("name"),
            "description": asset_data.get("description"),
            "file_path": asset_data.get("file_path"),
            "file_name": asset_data.get("file_name"),
            "file_extension": asset_data.get("file_extension"),
            "file_size": asset_data.get("file_size"),
            "mime_type": asset_data.get("mime_type"),
            "asset_type": asset_data.get("asset_type"),
            "status": asset_data.get("status"),
            "tags": asset_data.get("tags", []),
            "project_id": asset_data.get("project_id"),
            "created_by": asset_data.get("created_by"),
            "created_at": asset_data.get("created_at"),
            "updated_at": asset_data.get("updated_at"),
            "checksum": asset_data.get("checksum"),
            "version": asset_data.get("version", 1),
            "storage_location": asset_data.get("storage_location"),
            "is_proxy": asset_data.get("is_proxy", False),
            "proxy_type": asset_data.get("proxy_type"),
            "original_asset_id": asset_data.get("original_asset_id")
        }
    
    def _transform_metadata_data(self, metadata_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform metadata for search indexing"""
        return {
            "asset_id": metadata_data.get("asset_id"),
            "metadata_id": metadata_data.get("metadata_id"),
            "schema_id": metadata_data.get("schema_id"),
            "schema_name": metadata_data.get("schema_name"),
            "title": metadata_data.get("title"),
            "description": metadata_data.get("description"),
            "keywords": metadata_data.get("keywords", []),
            "tags": metadata_data.get("tags", []),
            "custom_fields": metadata_data.get("custom_fields", {}),
            "technical_metadata": metadata_data.get("technical_metadata", {}),
            "extracted_text": metadata_data.get("extracted_text"),
            "created_at": metadata_data.get("created_at"),
            "updated_at": metadata_data.get("updated_at"),
            "version": metadata_data.get("version", 1)
        }
    
    def _transform_content_data(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform content data for search indexing"""
        return {
            "asset_id": content_data.get("asset_id"),
            "content_id": content_data.get("content_id"),
            "content_type": content_data.get("content_type"),
            "title": content_data.get("title"),
            "content": content_data.get("content"),
            "transcript": content_data.get("transcript"),
            "ocr_text": content_data.get("ocr_text"),
            "subtitle_text": content_data.get("subtitle_text"),
            "language": content_data.get("language"),
            "confidence": content_data.get("confidence"),
            "created_at": content_data.get("created_at"),
            "updated_at": content_data.get("updated_at")
        }


async def get_data_pipeline() -> DataPipeline:
    """Get data pipeline service instance"""
    indexing_service = await get_indexing_service()
    return DataPipeline(indexing_service)