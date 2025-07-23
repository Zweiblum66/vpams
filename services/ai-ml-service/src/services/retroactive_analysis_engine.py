"""
Retroactive Analysis Engine

This engine processes previously analyzed assets when new entities are added to the knowledge base.
It can retroactively apply recognition to all archived content.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime
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
    RetroactiveAnalysisJob
)
from .knowledge_base_service import KnowledgeBaseService


class RetroactiveAnalysisEngine:
    """Engine for retroactive analysis of archived content."""
    
    def __init__(self, model_manager, knowledge_base_service: KnowledgeBaseService):
        self.model_manager = model_manager
        self.knowledge_base_service = knowledge_base_service
        self.logger = MLLogger("retroactive_analysis")
        self._running_jobs = {}  # Track running jobs
        
    async def process_retroactive_analysis_job(
        self,
        job_id: str,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process a retroactive analysis job.
        
        Args:
            job_id: ID of the job to process
            batch_size: Number of assets to process in each batch
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary containing job results
        """
        try:
            async with get_db_session() as session:
                # Get job details
                job_result = await session.execute(
                    select(RetroactiveAnalysisJob, KnowledgeEntity).join(
                        KnowledgeEntity, RetroactiveAnalysisJob.entity_id == KnowledgeEntity.id
                    ).where(RetroactiveAnalysisJob.id == uuid.UUID(job_id))
                )
                job_data = job_result.first()
                
                if not job_data:
                    raise ValidationError(f"Job {job_id} not found")
                
                job, entity = job_data
                
                if job.status != "pending":
                    raise ValidationError(f"Job {job_id} is not pending")
                
                # Mark job as running
                job.status = "running"
                job.started_at = datetime.utcnow()
                await session.commit()
                
                self._running_jobs[job_id] = {
                    "job": job,
                    "entity": entity,
                    "start_time": time.time()
                }
            
            # Process the job
            results = await self._execute_retroactive_analysis(
                job, entity, batch_size, progress_callback
            )
            
            # Update job status
            async with get_db_session() as session:
                job_update = await session.execute(
                    select(RetroactiveAnalysisJob).where(
                        RetroactiveAnalysisJob.id == uuid.UUID(job_id)
                    )
                )
                job = job_update.scalar_one()
                
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.matches_found = results["matches_found"]
                job.processed_assets = results["processed_assets"]
                job.processing_errors = results["processing_errors"]
                
                await session.commit()
            
            # Remove from running jobs
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
            
            self.logger.logger.info(
                "Retroactive analysis job completed",
                job_id=job_id,
                entity_type=entity.entity_type,
                entity_id=entity.entity_id,
                matches_found=results["matches_found"],
                processed_assets=results["processed_assets"],
                processing_time=time.time() - self._running_jobs.get(job_id, {}).get("start_time", 0)
            )
            
            return results
            
        except Exception as e:
            # Mark job as failed
            try:
                async with get_db_session() as session:
                    job_update = await session.execute(
                        select(RetroactiveAnalysisJob).where(
                            RetroactiveAnalysisJob.id == uuid.UUID(job_id)
                        )
                    )
                    job = job_update.scalar_one_or_none()
                    
                    if job:
                        job.status = "failed"
                        job.error_details = {"error": str(e)}
                        await session.commit()
            except:
                pass
            
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]
            
            self.logger.log_error("process_retroactive_analysis_job", str(e), job_id=job_id)
            raise InferenceError(f"Retroactive analysis job failed: {e}")
    
    async def _execute_retroactive_analysis(
        self,
        job: RetroactiveAnalysisJob,
        entity: KnowledgeEntity,
        batch_size: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Execute the retroactive analysis."""
        try:
            # Get entity features
            entity_features = await self._get_entity_features(entity.id)
            
            if not entity_features:
                raise ValidationError(f"No features found for entity {entity.entity_id}")
            
            # Get assets to analyze
            assets_to_analyze = await self._get_assets_to_analyze(job, entity)
            
            # Update job with total count
            async with get_db_session() as session:
                job_update = await session.execute(
                    select(RetroactiveAnalysisJob).where(
                        RetroactiveAnalysisJob.id == job.id
                    )
                )
                job_obj = job_update.scalar_one()
                job_obj.total_assets = len(assets_to_analyze)
                await session.commit()
            
            # Process in batches
            matches_found = 0
            processed_assets = 0
            processing_errors = 0
            
            for i in range(0, len(assets_to_analyze), batch_size):
                batch = assets_to_analyze[i:i + batch_size]
                
                try:
                    batch_results = await self._process_asset_batch(
                        batch, entity, entity_features, job.job_type
                    )
                    
                    matches_found += batch_results["matches_found"]
                    processed_assets += batch_results["processed_assets"]
                    processing_errors += batch_results["processing_errors"]
                    
                    # Update progress
                    if progress_callback:
                        progress = {
                            "processed_assets": processed_assets,
                            "total_assets": len(assets_to_analyze),
                            "matches_found": matches_found,
                            "processing_errors": processing_errors,
                            "progress_percentage": (processed_assets / len(assets_to_analyze)) * 100
                        }
                        await progress_callback(progress)
                    
                    # Update job progress
                    async with get_db_session() as session:
                        job_update = await session.execute(
                            select(RetroactiveAnalysisJob).where(
                                RetroactiveAnalysisJob.id == job.id
                            )
                        )
                        job_obj = job_update.scalar_one()
                        job_obj.processed_assets = processed_assets
                        job_obj.matched_assets = matches_found
                        await session.commit()
                    
                except Exception as e:
                    self.logger.log_error("batch_processing", str(e), batch_start=i)
                    processing_errors += len(batch)
                    processed_assets += len(batch)
            
            return {
                "matches_found": matches_found,
                "processed_assets": processed_assets,
                "processing_errors": processing_errors,
                "total_assets": len(assets_to_analyze)
            }
            
        except Exception as e:
            self.logger.log_error("execute_retroactive_analysis", str(e))
            raise InferenceError(f"Failed to execute retroactive analysis: {e}")
    
    async def _get_entity_features(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        """Get features for an entity."""
        try:
            async with get_db_session() as session:
                features_result = await session.execute(
                    select(EntityFeature).where(
                        EntityFeature.entity_id == entity_id
                    )
                )
                features = features_result.scalars().all()
                
                entity_features = {}
                for feature in features:
                    import pickle
                    feature_vector = pickle.loads(feature.feature_vector)
                    entity_features[feature.feature_type] = {
                        "vector": feature_vector,
                        "metadata": feature.feature_metadata,
                        "quality_score": feature.quality_score
                    }
                
                return entity_features
                
        except Exception as e:
            self.logger.log_error("get_entity_features", str(e))
            return {}
    
    async def _get_assets_to_analyze(
        self,
        job: RetroactiveAnalysisJob,
        entity: KnowledgeEntity
    ) -> List[Dict[str, Any]]:
        """Get list of assets to analyze."""
        try:
            async with get_db_session() as session:
                # Base query
                query = select(AnalysisIndex)
                
                # Apply scope filters
                if job.analysis_scope == "date_range":
                    if job.start_date:
                        query = query.where(AnalysisIndex.created_at >= job.start_date)
                    if job.end_date:
                        query = query.where(AnalysisIndex.created_at <= job.end_date)
                
                elif job.analysis_scope == "asset_list":
                    if job.asset_ids:
                        query = query.where(AnalysisIndex.asset_id.in_(job.asset_ids))
                
                # Filter by analysis type
                if entity.entity_type == "person":
                    query = query.where(AnalysisIndex.faces_analyzed == True)
                elif entity.entity_type == "logo":
                    query = query.where(AnalysisIndex.logos_analyzed == True)
                elif entity.entity_type == "speaker":
                    query = query.where(AnalysisIndex.speakers_analyzed == True)
                elif entity.entity_type == "object":
                    query = query.where(AnalysisIndex.objects_analyzed == True)
                
                result = await session.execute(query)
                assets = result.scalars().all()
                
                # Convert to list of dictionaries
                assets_list = []
                for asset in assets:
                    asset_data = {
                        "asset_id": str(asset.asset_id),
                        "asset_type": asset.asset_type,
                        "asset_path": asset.asset_path,
                        "features": {}
                    }
                    
                    # Add relevant features
                    if entity.entity_type == "person" and asset.face_features:
                        asset_data["features"]["face_features"] = asset.face_features
                    elif entity.entity_type == "logo" and asset.logo_features:
                        asset_data["features"]["logo_features"] = asset.logo_features
                    elif entity.entity_type == "speaker" and asset.voice_features:
                        asset_data["features"]["voice_features"] = asset.voice_features
                    elif entity.entity_type == "object" and asset.object_features:
                        asset_data["features"]["object_features"] = asset.object_features
                    
                    assets_list.append(asset_data)
                
                return assets_list
                
        except Exception as e:
            self.logger.log_error("get_assets_to_analyze", str(e))
            return []
    
    async def _process_asset_batch(
        self,
        assets: List[Dict[str, Any]],
        entity: KnowledgeEntity,
        entity_features: Dict[str, Any],
        job_type: str
    ) -> Dict[str, Any]:
        """Process a batch of assets."""
        matches_found = 0
        processed_assets = 0
        processing_errors = 0
        
        for asset in assets:
            try:
                # Find matches for this asset
                matches = await self._find_matches_in_asset(
                    asset, entity, entity_features, job_type
                )
                
                if matches:
                    # Record the matches
                    await self.knowledge_base_service.record_detection(
                        asset_id=asset["asset_id"],
                        entity_matches=matches,
                        detection_type=entity.entity_type,
                        asset_type=asset["asset_type"]
                    )
                    matches_found += len(matches)
                
                processed_assets += 1
                
            except Exception as e:
                self.logger.log_error("process_asset", str(e), asset_id=asset["asset_id"])
                processing_errors += 1
                processed_assets += 1
        
        return {
            "matches_found": matches_found,
            "processed_assets": processed_assets,
            "processing_errors": processing_errors
        }
    
    async def _find_matches_in_asset(
        self,
        asset: Dict[str, Any],
        entity: KnowledgeEntity,
        entity_features: Dict[str, Any],
        job_type: str
    ) -> List[Dict[str, Any]]:
        """Find matches for an entity in an asset."""
        matches = []
        
        try:
            asset_features = asset.get("features", {})
            
            # Determine which features to compare
            if job_type == "person_match" and "face_features" in asset_features:
                matches = await self._compare_face_features(
                    asset_features["face_features"],
                    entity_features,
                    entity.confidence_threshold
                )
            
            elif job_type == "logo_match" and "logo_features" in asset_features:
                matches = await self._compare_logo_features(
                    asset_features["logo_features"],
                    entity_features,
                    entity.confidence_threshold
                )
            
            elif job_type == "speaker_match" and "voice_features" in asset_features:
                matches = await self._compare_voice_features(
                    asset_features["voice_features"],
                    entity_features,
                    entity.confidence_threshold
                )
            
            elif job_type == "object_match" and "object_features" in asset_features:
                matches = await self._compare_object_features(
                    asset_features["object_features"],
                    entity_features,
                    entity.confidence_threshold
                )
            
            # Add entity information to matches
            for match in matches:
                match.update({
                    "entity_id": entity.id,
                    "entity_type": entity.entity_type,
                    "entity_identifier": entity.entity_id,
                    "entity_name": entity.entity_name
                })
            
            return matches
            
        except Exception as e:
            self.logger.log_error("find_matches_in_asset", str(e))
            return []
    
    async def _compare_face_features(
        self,
        asset_face_features: List[Dict[str, Any]],
        entity_features: Dict[str, Any],
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Compare face features."""
        matches = []
        
        if "face_embedding" not in entity_features:
            return matches
        
        entity_embedding = entity_features["face_embedding"]["vector"]
        
        for face_feature in asset_face_features:
            if "embedding" in face_feature:
                asset_embedding = np.array(face_feature["embedding"])
                
                # Calculate similarity
                similarity = await self.knowledge_base_service._calculate_similarity(
                    entity_embedding, asset_embedding, "face_embedding"
                )
                
                if similarity >= confidence_threshold:
                    matches.append({
                        "confidence": similarity,
                        "bbox": face_feature.get("bbox"),
                        "feature_type": "face_embedding",
                        "similarity": similarity
                    })
        
        return matches
    
    async def _compare_logo_features(
        self,
        asset_logo_features: List[Dict[str, Any]],
        entity_features: Dict[str, Any],
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Compare logo features."""
        matches = []
        
        if "logo_embedding" not in entity_features:
            return matches
        
        entity_embedding = entity_features["logo_embedding"]["vector"]
        
        for logo_feature in asset_logo_features:
            if "embedding" in logo_feature:
                asset_embedding = np.array(logo_feature["embedding"])
                
                # Calculate similarity
                similarity = await self.knowledge_base_service._calculate_similarity(
                    entity_embedding, asset_embedding, "logo_embedding"
                )
                
                if similarity >= confidence_threshold:
                    matches.append({
                        "confidence": similarity,
                        "bbox": logo_feature.get("bbox"),
                        "feature_type": "logo_embedding",
                        "similarity": similarity
                    })
        
        return matches
    
    async def _compare_voice_features(
        self,
        asset_voice_features: List[Dict[str, Any]],
        entity_features: Dict[str, Any],
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Compare voice features."""
        matches = []
        
        if "voice_print" not in entity_features:
            return matches
        
        entity_voice_print = entity_features["voice_print"]["vector"]
        
        for voice_feature in asset_voice_features:
            if "voice_print" in voice_feature:
                asset_voice_print = np.array(voice_feature["voice_print"])
                
                # Calculate similarity
                similarity = await self.knowledge_base_service._calculate_similarity(
                    entity_voice_print, asset_voice_print, "voice_print"
                )
                
                if similarity >= confidence_threshold:
                    matches.append({
                        "confidence": similarity,
                        "start_time": voice_feature.get("start_time"),
                        "end_time": voice_feature.get("end_time"),
                        "feature_type": "voice_print",
                        "similarity": similarity
                    })
        
        return matches
    
    async def _compare_object_features(
        self,
        asset_object_features: List[Dict[str, Any]],
        entity_features: Dict[str, Any],
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Compare object features."""
        matches = []
        
        if "object_embedding" not in entity_features:
            return matches
        
        entity_embedding = entity_features["object_embedding"]["vector"]
        
        for object_feature in asset_object_features:
            if "embedding" in object_feature:
                asset_embedding = np.array(object_feature["embedding"])
                
                # Calculate similarity
                similarity = await self.knowledge_base_service._calculate_similarity(
                    entity_embedding, asset_embedding, "object_embedding"
                )
                
                if similarity >= confidence_threshold:
                    matches.append({
                        "confidence": similarity,
                        "bbox": object_feature.get("bbox"),
                        "feature_type": "object_embedding",
                        "similarity": similarity
                    })
        
        return matches
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a retroactive analysis job."""
        try:
            async with get_db_session() as session:
                job_result = await session.execute(
                    select(RetroactiveAnalysisJob).where(
                        RetroactiveAnalysisJob.id == uuid.UUID(job_id)
                    )
                )
                job = job_result.scalar_one_or_none()
                
                if not job:
                    raise ValidationError(f"Job {job_id} not found")
                
                progress_percentage = 0.0
                if job.total_assets > 0:
                    progress_percentage = (job.processed_assets / job.total_assets) * 100
                
                return {
                    "job_id": str(job.id),
                    "entity_id": str(job.entity_id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "progress_percentage": progress_percentage,
                    "total_assets": job.total_assets,
                    "processed_assets": job.processed_assets,
                    "matches_found": job.matches_found,
                    "processing_errors": job.processing_errors,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
                
        except Exception as e:
            self.logger.log_error("get_job_status", str(e))
            raise InferenceError(f"Failed to get job status: {e}")
    
    async def list_pending_jobs(self) -> List[Dict[str, Any]]:
        """List all pending retroactive analysis jobs."""
        try:
            async with get_db_session() as session:
                jobs_result = await session.execute(
                    select(RetroactiveAnalysisJob, KnowledgeEntity).join(
                        KnowledgeEntity, RetroactiveAnalysisJob.entity_id == KnowledgeEntity.id
                    ).where(RetroactiveAnalysisJob.status == "pending")
                    .order_by(RetroactiveAnalysisJob.created_at)
                )
                
                jobs = []
                for job, entity in jobs_result.all():
                    jobs.append({
                        "job_id": str(job.id),
                        "entity_id": str(entity.id),
                        "entity_type": entity.entity_type,
                        "entity_identifier": entity.entity_id,
                        "entity_name": entity.entity_name,
                        "job_type": job.job_type,
                        "analysis_scope": job.analysis_scope,
                        "created_at": job.created_at.isoformat()
                    })
                
                return jobs
                
        except Exception as e:
            self.logger.log_error("list_pending_jobs", str(e))
            return []