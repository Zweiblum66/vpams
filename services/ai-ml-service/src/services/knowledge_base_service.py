"""
Knowledge Base Service

This service manages the persistent knowledge base for archive-based recognition.
It allows adding new entities and retroactively applying recognition to all analyzed content.
"""

import asyncio
import time
import pickle
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
from datetime import datetime, timedelta
import numpy as np

from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from ..db.base import get_db_session
from ..db.knowledge_base_models import (
    KnowledgeEntity, EntityFeature, EntityDetection, AnalysisIndex,
    RetroactiveAnalysisJob, EntityRelationship, EntityAnnotation
)


class KnowledgeBaseService:
    """Service for managing the persistent knowledge base."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.logger = MLLogger("knowledge_base")
        
    async def add_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        confidence_threshold: float = 0.7,
        features: Optional[Dict[str, Any]] = None,
        trigger_retroactive_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new entity to the knowledge base.
        
        Args:
            entity_type: Type of entity (person, logo, object, speaker, etc.)
            entity_id: Unique identifier for the entity
            entity_name: Display name
            description: Optional description
            tags: Optional tags
            categories: Optional categories
            confidence_threshold: Minimum confidence for matching
            features: Optional initial features (embeddings, etc.)
            trigger_retroactive_analysis: Whether to trigger retroactive analysis
            
        Returns:
            Dictionary containing the created entity information
        """
        try:
            async with get_db_session() as session:
                # Check if entity already exists
                existing_entity = await session.execute(
                    select(KnowledgeEntity).where(
                        and_(
                            KnowledgeEntity.entity_type == entity_type,
                            KnowledgeEntity.entity_id == entity_id
                        )
                    )
                )
                
                if existing_entity.scalar_one_or_none():
                    raise ValidationError(f"Entity {entity_type}:{entity_id} already exists")
                
                # Create new entity
                entity = KnowledgeEntity(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    description=description,
                    tags=tags or [],
                    categories=categories or [],
                    confidence_threshold=confidence_threshold
                )
                
                session.add(entity)
                await session.flush()
                
                # Add features if provided
                feature_count = 0
                if features:
                    for feature_type, feature_data in features.items():
                        await self._add_entity_feature(
                            session, entity.id, feature_type, feature_data
                        )
                        feature_count += 1
                
                await session.commit()
                
                # Trigger retroactive analysis if requested
                if trigger_retroactive_analysis:
                    await self._trigger_retroactive_analysis(entity.id, entity_type)
                
                self.logger.logger.info(
                    "Entity added to knowledge base",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    feature_count=feature_count
                )
                
                return {
                    "id": str(entity.id),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "feature_count": feature_count,
                    "retroactive_analysis_triggered": trigger_retroactive_analysis
                }
                
        except Exception as e:
            self.logger.log_error("add_entity", str(e), entity_type=entity_type, entity_id=entity_id)
            raise InferenceError(f"Failed to add entity: {e}")
    
    async def add_entity_from_detection(
        self,
        asset_id: str,
        detection_data: Dict[str, Any],
        entity_type: str,
        entity_id: str,
        entity_name: str,
        trigger_retroactive_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Add an entity based on a detection in an asset.
        
        Args:
            asset_id: ID of the asset containing the detection
            detection_data: Detection data (bbox, features, etc.)
            entity_type: Type of entity
            entity_id: Unique identifier
            entity_name: Display name
            trigger_retroactive_analysis: Whether to trigger retroactive analysis
            
        Returns:
            Dictionary containing the created entity information
        """
        try:
            # Extract features from detection
            features = {}
            if entity_type == "person" and "face_embedding" in detection_data:
                features["face_embedding"] = detection_data["face_embedding"]
            elif entity_type == "logo" and "logo_embedding" in detection_data:
                features["logo_embedding"] = detection_data["logo_embedding"]
            elif entity_type == "speaker" and "voice_print" in detection_data:
                features["voice_print"] = detection_data["voice_print"]
            
            # Add entity
            result = await self.add_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                features=features,
                trigger_retroactive_analysis=trigger_retroactive_analysis
            )
            
            # Record the source detection
            async with get_db_session() as session:
                entity_uuid = uuid.UUID(result["id"])
                
                detection = EntityDetection(
                    entity_id=entity_uuid,
                    asset_id=uuid.UUID(asset_id),
                    asset_type=detection_data.get("asset_type", "unknown"),
                    detection_type=entity_type,
                    confidence=detection_data.get("confidence", 1.0),
                    bbox_x=detection_data.get("bbox", {}).get("x"),
                    bbox_y=detection_data.get("bbox", {}).get("y"),
                    bbox_width=detection_data.get("bbox", {}).get("width"),
                    bbox_height=detection_data.get("bbox", {}).get("height"),
                    start_time=detection_data.get("start_time"),
                    end_time=detection_data.get("end_time"),
                    detection_metadata=detection_data,
                    is_verified=True  # This is the source detection
                )
                
                session.add(detection)
                await session.commit()
            
            return result
            
        except Exception as e:
            self.logger.log_error("add_entity_from_detection", str(e))
            raise InferenceError(f"Failed to add entity from detection: {e}")
    
    async def find_matches(
        self,
        features: Dict[str, Any],
        entity_type: str,
        confidence_threshold: Optional[float] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find matching entities based on features.
        
        Args:
            features: Feature data to match against
            entity_type: Type of entity to match
            confidence_threshold: Minimum confidence threshold
            max_results: Maximum number of results
            
        Returns:
            List of matching entities with similarity scores
        """
        try:
            async with get_db_session() as session:
                # Get all entities of the specified type
                entities_result = await session.execute(
                    select(KnowledgeEntity).where(
                        and_(
                            KnowledgeEntity.entity_type == entity_type,
                            KnowledgeEntity.is_active == True
                        )
                    )
                )
                entities = entities_result.scalars().all()
                
                matches = []
                
                for entity in entities:
                    # Get entity features
                    features_result = await session.execute(
                        select(EntityFeature).where(
                            EntityFeature.entity_id == entity.id
                        )
                    )
                    entity_features = features_result.scalars().all()
                    
                    # Calculate similarity for each feature type
                    best_similarity = 0.0
                    best_feature_type = None
                    
                    for entity_feature in entity_features:
                        feature_type = entity_feature.feature_type
                        
                        if feature_type in features:
                            # Deserialize stored feature
                            stored_feature = pickle.loads(entity_feature.feature_vector)
                            input_feature = features[feature_type]
                            
                            # Calculate similarity
                            similarity = await self._calculate_similarity(
                                stored_feature, input_feature, feature_type
                            )
                            
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_feature_type = feature_type
                    
                    # Check confidence threshold
                    threshold = confidence_threshold or entity.confidence_threshold
                    if best_similarity >= threshold:
                        matches.append({
                            "entity_id": entity.id,
                            "entity_type": entity.entity_type,
                            "entity_identifier": entity.entity_id,
                            "entity_name": entity.entity_name,
                            "similarity": best_similarity,
                            "confidence": best_similarity,
                            "feature_type": best_feature_type,
                            "description": entity.description,
                            "tags": entity.tags,
                            "categories": entity.categories
                        })
                
                # Sort by similarity and limit results
                matches.sort(key=lambda x: x["similarity"], reverse=True)
                return matches[:max_results]
                
        except Exception as e:
            self.logger.log_error("find_matches", str(e))
            raise InferenceError(f"Failed to find matches: {e}")
    
    async def record_detection(
        self,
        asset_id: str,
        entity_matches: List[Dict[str, Any]],
        detection_type: str,
        asset_type: str = "unknown",
        processing_job_id: Optional[str] = None
    ) -> int:
        """
        Record detections of entities in an asset.
        
        Args:
            asset_id: ID of the asset
            entity_matches: List of entity matches
            detection_type: Type of detection
            asset_type: Type of asset
            processing_job_id: Optional processing job ID
            
        Returns:
            Number of detections recorded
        """
        try:
            async with get_db_session() as session:
                detections_added = 0
                
                for match in entity_matches:
                    detection = EntityDetection(
                        entity_id=uuid.UUID(str(match["entity_id"])),
                        asset_id=uuid.UUID(asset_id),
                        asset_type=asset_type,
                        detection_type=detection_type,
                        confidence=match["confidence"],
                        bbox_x=match.get("bbox", {}).get("x"),
                        bbox_y=match.get("bbox", {}).get("y"),
                        bbox_width=match.get("bbox", {}).get("width"),
                        bbox_height=match.get("bbox", {}).get("height"),
                        start_time=match.get("start_time"),
                        end_time=match.get("end_time"),
                        detection_metadata=match,
                        processing_job_id=uuid.UUID(processing_job_id) if processing_job_id else None
                    )
                    
                    session.add(detection)
                    detections_added += 1
                
                await session.commit()
                
                self.logger.logger.info(
                    "Detections recorded",
                    asset_id=asset_id,
                    detection_type=detection_type,
                    detections_count=detections_added
                )
                
                return detections_added
                
        except Exception as e:
            self.logger.log_error("record_detection", str(e))
            raise InferenceError(f"Failed to record detection: {e}")
    
    async def get_asset_entities(
        self,
        asset_id: str,
        entity_types: Optional[List[str]] = None,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Get all entities detected in an asset.
        
        Args:
            asset_id: ID of the asset
            entity_types: Optional filter by entity types
            include_metadata: Whether to include metadata
            
        Returns:
            Dictionary containing detected entities
        """
        try:
            async with get_db_session() as session:
                # Build query
                query = select(EntityDetection, KnowledgeEntity).join(
                    KnowledgeEntity, EntityDetection.entity_id == KnowledgeEntity.id
                ).where(EntityDetection.asset_id == uuid.UUID(asset_id))
                
                if entity_types:
                    query = query.where(KnowledgeEntity.entity_type.in_(entity_types))
                
                result = await session.execute(query)
                detections = result.all()
                
                # Group by entity type
                entities_by_type = {}
                
                for detection, entity in detections:
                    entity_type = entity.entity_type
                    
                    if entity_type not in entities_by_type:
                        entities_by_type[entity_type] = []
                    
                    entity_data = {
                        "entity_id": entity.entity_id,
                        "entity_name": entity.entity_name,
                        "confidence": detection.confidence,
                        "detection_id": str(detection.id),
                        "is_verified": detection.is_verified
                    }
                    
                    # Add spatial/temporal information
                    if detection.bbox_x is not None:
                        entity_data["bbox"] = {
                            "x": detection.bbox_x,
                            "y": detection.bbox_y,
                            "width": detection.bbox_width,
                            "height": detection.bbox_height
                        }
                    
                    if detection.start_time is not None:
                        entity_data["timespan"] = {
                            "start": detection.start_time,
                            "end": detection.end_time
                        }
                    
                    if include_metadata:
                        entity_data["description"] = entity.description
                        entity_data["tags"] = entity.tags
                        entity_data["categories"] = entity.categories
                        entity_data["detection_metadata"] = detection.detection_metadata
                    
                    entities_by_type[entity_type].append(entity_data)
                
                return {
                    "asset_id": asset_id,
                    "entities": entities_by_type,
                    "total_detections": len(detections)
                }
                
        except Exception as e:
            self.logger.log_error("get_asset_entities", str(e))
            raise InferenceError(f"Failed to get asset entities: {e}")
    
    async def update_analysis_index(
        self,
        asset_id: str,
        asset_type: str,
        analysis_type: str,
        features: Optional[Dict[str, Any]] = None,
        asset_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update the analysis index for an asset.
        
        Args:
            asset_id: ID of the asset
            asset_type: Type of asset
            analysis_type: Type of analysis performed
            features: Extracted features
            asset_metadata: Asset metadata
        """
        try:
            async with get_db_session() as session:
                # Get or create analysis index entry
                result = await session.execute(
                    select(AnalysisIndex).where(
                        AnalysisIndex.asset_id == uuid.UUID(asset_id)
                    )
                )
                analysis_index = result.scalar_one_or_none()
                
                if not analysis_index:
                    analysis_index = AnalysisIndex(
                        asset_id=uuid.UUID(asset_id),
                        asset_type=asset_type,
                        asset_path=asset_metadata.get("path") if asset_metadata else None,
                        asset_size=asset_metadata.get("size") if asset_metadata else None,
                        asset_duration=asset_metadata.get("duration") if asset_metadata else None
                    )
                    session.add(analysis_index)
                
                # Update analysis status
                now = datetime.utcnow()
                
                if analysis_type == "faces":
                    analysis_index.faces_analyzed = True
                    analysis_index.faces_analyzed_at = now
                    if features and "face_features" in features:
                        analysis_index.face_features = features["face_features"]
                
                elif analysis_type == "objects":
                    analysis_index.objects_analyzed = True
                    analysis_index.objects_analyzed_at = now
                    if features and "object_features" in features:
                        analysis_index.object_features = features["object_features"]
                
                elif analysis_type == "logos":
                    analysis_index.logos_analyzed = True
                    analysis_index.logos_analyzed_at = now
                    if features and "logo_features" in features:
                        analysis_index.logo_features = features["logo_features"]
                
                elif analysis_type == "speakers":
                    analysis_index.speakers_analyzed = True
                    analysis_index.speakers_analyzed_at = now
                    if features and "voice_features" in features:
                        analysis_index.voice_features = features["voice_features"]
                
                elif analysis_type == "scenes":
                    analysis_index.scenes_analyzed = True
                    analysis_index.scenes_analyzed_at = now
                
                analysis_index.last_analyzed = now
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("update_analysis_index", str(e))
            raise InferenceError(f"Failed to update analysis index: {e}")
    
    async def _add_entity_feature(
        self,
        session: AsyncSession,
        entity_id: uuid.UUID,
        feature_type: str,
        feature_data: Dict[str, Any]
    ) -> None:
        """Add a feature to an entity."""
        # Serialize feature vector
        feature_vector = pickle.dumps(feature_data.get("vector", feature_data))
        
        entity_feature = EntityFeature(
            entity_id=entity_id,
            feature_type=feature_type,
            feature_version=feature_data.get("version", "1.0"),
            feature_vector=feature_vector,
            feature_metadata=feature_data.get("metadata", {}),
            quality_score=feature_data.get("quality_score"),
            extraction_confidence=feature_data.get("confidence"),
            source_asset_id=uuid.UUID(feature_data["source_asset_id"]) if feature_data.get("source_asset_id") else None,
            source_bbox=feature_data.get("source_bbox"),
            source_timestamp=feature_data.get("source_timestamp")
        )
        
        session.add(entity_feature)
    
    async def _calculate_similarity(
        self,
        feature1: np.ndarray,
        feature2: np.ndarray,
        feature_type: str
    ) -> float:
        """Calculate similarity between two features."""
        if feature_type in ["face_embedding", "logo_embedding", "voice_print"]:
            # Cosine similarity for embeddings
            dot_product = np.dot(feature1, feature2)
            norm1 = np.linalg.norm(feature1)
            norm2 = np.linalg.norm(feature2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, similarity)  # Ensure non-negative
        
        else:
            # Euclidean distance for other features
            distance = np.linalg.norm(feature1 - feature2)
            # Convert to similarity (0-1 range)
            return 1.0 / (1.0 + distance)
    
    async def _trigger_retroactive_analysis(
        self,
        entity_id: uuid.UUID,
        entity_type: str
    ) -> None:
        """Trigger retroactive analysis for a new entity."""
        try:
            async with get_db_session() as session:
                # Create retroactive analysis job
                job = RetroactiveAnalysisJob(
                    entity_id=entity_id,
                    job_type=f"{entity_type}_match",
                    analysis_scope="all",
                    status="pending"
                )
                
                session.add(job)
                await session.commit()
                
                # Queue the job for processing (would integrate with task queue)
                self.logger.logger.info(
                    "Retroactive analysis job created",
                    entity_id=str(entity_id),
                    entity_type=entity_type,
                    job_id=str(job.id)
                )
                
        except Exception as e:
            self.logger.log_error("trigger_retroactive_analysis", str(e))
    
    async def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            async with get_db_session() as session:
                # Count entities by type
                entities_result = await session.execute(
                    select(KnowledgeEntity.entity_type, func.count(KnowledgeEntity.id))
                    .group_by(KnowledgeEntity.entity_type)
                    .where(KnowledgeEntity.is_active == True)
                )
                entities_by_type = {row[0]: row[1] for row in entities_result.all()}
                
                # Count total detections
                detections_result = await session.execute(
                    select(func.count(EntityDetection.id))
                )
                total_detections = detections_result.scalar()
                
                # Count analyzed assets
                analyzed_assets_result = await session.execute(
                    select(func.count(AnalysisIndex.id))
                )
                analyzed_assets = analyzed_assets_result.scalar()
                
                # Get recent activity
                recent_entities_result = await session.execute(
                    select(func.count(KnowledgeEntity.id))
                    .where(KnowledgeEntity.created_at >= datetime.utcnow() - timedelta(days=7))
                )
                recent_entities = recent_entities_result.scalar()
                
                return {
                    "entities_by_type": entities_by_type,
                    "total_entities": sum(entities_by_type.values()),
                    "total_detections": total_detections,
                    "analyzed_assets": analyzed_assets,
                    "recent_entities": recent_entities
                }
                
        except Exception as e:
            self.logger.log_error("get_knowledge_base_stats", str(e))
            return {}
    
    async def search_entities(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search entities in the knowledge base.
        
        Args:
            query: Search query
            entity_types: Optional filter by entity types
            tags: Optional filter by tags
            categories: Optional filter by categories
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        try:
            async with get_db_session() as session:
                # Build search query
                search_query = select(KnowledgeEntity).where(
                    KnowledgeEntity.is_active == True
                )
                
                if query:
                    search_query = search_query.where(
                        or_(
                            KnowledgeEntity.entity_name.ilike(f"%{query}%"),
                            KnowledgeEntity.entity_id.ilike(f"%{query}%"),
                            KnowledgeEntity.description.ilike(f"%{query}%")
                        )
                    )
                
                if entity_types:
                    search_query = search_query.where(
                        KnowledgeEntity.entity_type.in_(entity_types)
                    )
                
                if tags:
                    search_query = search_query.where(
                        KnowledgeEntity.tags.overlap(tags)
                    )
                
                if categories:
                    search_query = search_query.where(
                        KnowledgeEntity.categories.overlap(categories)
                    )
                
                search_query = search_query.limit(limit)
                
                result = await session.execute(search_query)
                entities = result.scalars().all()
                
                # Format results
                results = []
                for entity in entities:
                    results.append({
                        "id": str(entity.id),
                        "entity_type": entity.entity_type,
                        "entity_id": entity.entity_id,
                        "entity_name": entity.entity_name,
                        "description": entity.description,
                        "tags": entity.tags,
                        "categories": entity.categories,
                        "created_at": entity.created_at.isoformat(),
                        "last_matched": entity.last_matched.isoformat() if entity.last_matched else None
                    })
                
                return results
                
        except Exception as e:
            self.logger.log_error("search_entities", str(e))
            return []