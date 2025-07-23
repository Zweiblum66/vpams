"""
Content Recommendation Engine

Provides personalized content recommendations using collaborative and content-based filtering.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from aioredis import Redis
import structlog
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import pandas as pd
import json

from ..core.config import settings
from ..models.schemas import (
    ContentRecommendation, RecommendationRequest, RecommendationType,
    RecommendationReason, ModelType
)
from ..db.models import (
    ContentRecommendationModel, UsageHistoryModel, AssetMetadataModel,
    UserPreferenceModel
)
from ..utils.metrics import ai_metrics
from ..utils.feature_engineering import FeatureEngineer


logger = structlog.get_logger()


class RecommendationEngine:
    """Generates personalized content recommendations"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.feature_engineer = FeatureEngineer()
        self.model_version = "1.0.0"
        self.svd_model = None
        self.item_features = None
        self.user_item_matrix = None
    
    async def initialize(self):
        """Initialize recommendation engine"""
        logger.info("Initializing recommendation engine")
        
        # Load or train models
        await self._load_models()
        
        # Schedule periodic model updates
        asyncio.create_task(self._periodic_model_update())
    
    async def get_recommendations(
        self,
        request: RecommendationRequest,
        user_id: str
    ) -> List[ContentRecommendation]:
        """Generate content recommendations"""
        logger.info(
            "Generating recommendations",
            user_id=user_id,
            type=request.recommendation_type,
            count=request.count
        )
        
        # Check cache first
        cache_key = f"recommendations:{user_id}:{request.recommendation_type}:{request.count}"
        cached = await self.redis.get(cache_key)
        if cached and not request.force_refresh:
            return [ContentRecommendation(**r) for r in json.loads(cached)]
        
        # Generate recommendations based on type
        if request.recommendation_type == RecommendationType.SIMILAR:
            recommendations = await self._get_similar_content(
                request.reference_asset_id,
                request.count,
                request.filters
            )
        elif request.recommendation_type == RecommendationType.TRENDING:
            recommendations = await self._get_trending_content(
                request.count,
                request.filters
            )
        elif request.recommendation_type == RecommendationType.PERSONALIZED:
            recommendations = await self._get_personalized_recommendations(
                user_id,
                request.count,
                request.filters
            )
        elif request.recommendation_type == RecommendationType.COLLABORATIVE:
            recommendations = await self._get_collaborative_recommendations(
                user_id,
                request.count,
                request.filters
            )
        else:
            recommendations = await self._get_popular_content(
                request.count,
                request.filters
            )
        
        # Store recommendations
        for rec in recommendations:
            await self._store_recommendation(rec, user_id)
        
        # Cache results
        await self.redis.setex(
            cache_key,
            3600,  # 1 hour TTL
            json.dumps([r.dict() for r in recommendations])
        )
        
        # Update metrics
        ai_metrics.recommendations_generated.labels(
            type=request.recommendation_type.value
        ).inc(len(recommendations))
        
        return recommendations
    
    async def _get_similar_content(
        self,
        asset_id: str,
        count: int,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContentRecommendation]:
        """Find similar content using content-based filtering"""
        # Get asset metadata
        result = await self.db.execute(
            select(AssetMetadataModel).where(AssetMetadataModel.asset_id == asset_id)
        )
        asset_metadata = result.scalar_one_or_none()
        
        if not asset_metadata:
            return []
        
        # Extract features
        asset_features = await self._extract_asset_features(asset_metadata)
        
        # Find similar assets
        similarities = []
        
        # Query other assets
        query = select(AssetMetadataModel).where(
            AssetMetadataModel.asset_id != asset_id
        )
        
        # Apply filters
        if filters:
            if "type" in filters:
                query = query.where(AssetMetadataModel.asset_type == filters["type"])
            if "category" in filters:
                query = query.where(AssetMetadataModel.category == filters["category"])
        
        result = await self.db.execute(query.limit(1000))
        candidates = result.scalars().all()
        
        for candidate in candidates:
            candidate_features = await self._extract_asset_features(candidate)
            similarity = self._calculate_similarity(asset_features, candidate_features)
            
            if similarity > 0.5:  # Threshold
                similarities.append((candidate.asset_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Create recommendations
        recommendations = []
        for asset_id, score in similarities[:count]:
            rec = ContentRecommendation(
                asset_id=asset_id,
                recommendation_type=RecommendationType.SIMILAR,
                score=score,
                confidence=min(score * 1.2, 1.0),  # Boost confidence
                reasons=[
                    RecommendationReason(
                        type="similarity",
                        description=f"Similar to content you viewed",
                        weight=score
                    )
                ],
                model_version=self.model_version
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _get_trending_content(
        self,
        count: int,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContentRecommendation]:
        """Get trending content based on recent activity"""
        # Calculate trending score based on recent views
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        query = (
            select(
                UsageHistoryModel.asset_id,
                func.sum(UsageHistoryModel.access_count).label("total_views"),
                func.count(func.distinct(UsageHistoryModel.user_id)).label("unique_users")
            )
            .where(UsageHistoryModel.timestamp >= cutoff)
            .group_by(UsageHistoryModel.asset_id)
        )
        
        result = await self.db.execute(query)
        trending_assets = result.all()
        
        # Calculate trending scores
        trending_scores = []
        for asset_id, total_views, unique_users in trending_assets:
            # Trending score formula
            recency_weight = 1.0
            score = (total_views * 0.3 + unique_users * 0.7) * recency_weight
            trending_scores.append((asset_id, score, total_views, unique_users))
        
        # Sort by score
        trending_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Create recommendations
        recommendations = []
        for asset_id, score, views, users in trending_scores[:count]:
            rec = ContentRecommendation(
                asset_id=asset_id,
                recommendation_type=RecommendationType.TRENDING,
                score=min(score / 100, 1.0),  # Normalize
                confidence=0.9,
                reasons=[
                    RecommendationReason(
                        type="trending",
                        description=f"Viewed {views} times by {users} users this week",
                        weight=0.8
                    )
                ],
                model_version=self.model_version
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _get_personalized_recommendations(
        self,
        user_id: str,
        count: int,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContentRecommendation]:
        """Get personalized recommendations using hybrid approach"""
        # Get user preferences
        user_prefs = await self._get_user_preferences(user_id)
        
        # Get user history
        user_history = await self._get_user_history(user_id, limit=100)
        
        # Combine content-based and collaborative filtering
        content_based = await self._content_based_recommendations(
            user_id, user_history, user_prefs, count * 2
        )
        
        collaborative = await self._collaborative_filtering(
            user_id, count * 2
        )
        
        # Merge and rank
        all_recommendations = {}
        
        # Add content-based
        for rec in content_based:
            all_recommendations[rec.asset_id] = rec
        
        # Merge collaborative
        for rec in collaborative:
            if rec.asset_id in all_recommendations:
                # Combine scores
                existing = all_recommendations[rec.asset_id]
                existing.score = (existing.score + rec.score) / 2
                existing.reasons.extend(rec.reasons)
            else:
                all_recommendations[rec.asset_id] = rec
        
        # Sort by score
        sorted_recs = sorted(
            all_recommendations.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        return sorted_recs[:count]
    
    async def _get_collaborative_recommendations(
        self,
        user_id: str,
        count: int,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContentRecommendation]:
        """Pure collaborative filtering recommendations"""
        if self.svd_model is None or self.user_item_matrix is None:
            # Fallback to popular items
            return await self._get_popular_content(count, filters)
        
        try:
            # Get user index
            user_idx = await self._get_user_index(user_id)
            if user_idx is None:
                return await self._get_popular_content(count, filters)
            
            # Get predictions
            user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
            predictions = self.svd_model.inverse_transform(
                self.svd_model.transform([user_ratings])
            )[0]
            
            # Filter out already viewed items
            viewed_items = set(np.where(user_ratings > 0)[0])
            
            # Get top recommendations
            recommendations = []
            item_scores = [(i, score) for i, score in enumerate(predictions)
                          if i not in viewed_items]
            item_scores.sort(key=lambda x: x[1], reverse=True)
            
            for item_idx, score in item_scores[:count]:
                asset_id = await self._get_asset_id_from_index(item_idx)
                if asset_id:
                    rec = ContentRecommendation(
                        asset_id=asset_id,
                        recommendation_type=RecommendationType.COLLABORATIVE,
                        score=min(score, 1.0),
                        confidence=0.7,
                        reasons=[
                            RecommendationReason(
                                type="collaborative",
                                description="Users with similar preferences also viewed this",
                                weight=0.8
                            )
                        ],
                        model_version=self.model_version
                    )
                    recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            logger.error("Error in collaborative filtering", error=str(e))
            return await self._get_popular_content(count, filters)
    
    async def _get_popular_content(
        self,
        count: int,
        filters: Optional[Dict[str, str]] = None
    ) -> List[ContentRecommendation]:
        """Get popular content as fallback"""
        query = (
            select(
                UsageHistoryModel.asset_id,
                func.sum(UsageHistoryModel.access_count).label("total_views")
            )
            .group_by(UsageHistoryModel.asset_id)
            .order_by(func.sum(UsageHistoryModel.access_count).desc())
            .limit(count)
        )
        
        result = await self.db.execute(query)
        popular_assets = result.all()
        
        recommendations = []
        for asset_id, views in popular_assets:
            rec = ContentRecommendation(
                asset_id=asset_id,
                recommendation_type=RecommendationType.POPULAR,
                score=min(views / 1000, 1.0),  # Normalize
                confidence=0.8,
                reasons=[
                    RecommendationReason(
                        type="popular",
                        description=f"Viewed {views} times overall",
                        weight=0.7
                    )
                ],
                model_version=self.model_version
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _extract_asset_features(self, metadata: AssetMetadataModel) -> np.ndarray:
        """Extract feature vector from asset metadata"""
        features = []
        
        # Basic features
        features.append(hash(metadata.asset_type or "") % 100 / 100)
        features.append(hash(metadata.category or "") % 100 / 100)
        features.append(metadata.duration_seconds / 3600 if metadata.duration_seconds else 0)
        features.append(metadata.file_size / (1024**3) if metadata.file_size else 0)
        
        # Tag features (simplified)
        if metadata.tags:
            tag_vector = [0] * 50  # Fixed size tag vector
            for i, tag in enumerate(metadata.tags[:50]):
                tag_vector[i] = hash(tag) % 100 / 100
            features.extend(tag_vector)
        else:
            features.extend([0] * 50)
        
        return np.array(features)
    
    def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """Calculate cosine similarity between feature vectors"""
        similarity = cosine_similarity([features1], [features2])[0][0]
        return float(similarity)
    
    async def _get_user_preferences(self, user_id: str) -> Optional[UserPreferenceModel]:
        """Get user preferences"""
        result = await self.db.execute(
            select(UserPreferenceModel).where(UserPreferenceModel.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_user_history(self, user_id: str, limit: int = 100) -> List[str]:
        """Get user's viewing history"""
        result = await self.db.execute(
            select(UsageHistoryModel.asset_id)
            .where(UsageHistoryModel.user_id == user_id)
            .order_by(UsageHistoryModel.timestamp.desc())
            .limit(limit)
        )
        return [row[0] for row in result.all()]
    
    async def _content_based_recommendations(
        self,
        user_id: str,
        user_history: List[str],
        user_prefs: Optional[UserPreferenceModel],
        count: int
    ) -> List[ContentRecommendation]:
        """Generate content-based recommendations"""
        if not user_history:
            return []
        
        # Get features for user's historical items
        historical_features = []
        for asset_id in user_history[:20]:  # Last 20 items
            result = await self.db.execute(
                select(AssetMetadataModel).where(AssetMetadataModel.asset_id == asset_id)
            )
            metadata = result.scalar_one_or_none()
            if metadata:
                features = await self._extract_asset_features(metadata)
                historical_features.append(features)
        
        if not historical_features:
            return []
        
        # Create user profile as average of historical features
        user_profile = np.mean(historical_features, axis=0)
        
        # Find similar items
        recommendations = []
        
        # Query candidates
        query = select(AssetMetadataModel).where(
            ~AssetMetadataModel.asset_id.in_(user_history)
        ).limit(500)
        
        result = await self.db.execute(query)
        candidates = result.scalars().all()
        
        similarities = []
        for candidate in candidates:
            features = await self._extract_asset_features(candidate)
            similarity = self._calculate_similarity(user_profile, features)
            
            if similarity > 0.3:  # Threshold
                similarities.append((candidate.asset_id, similarity))
        
        # Sort and create recommendations
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        for asset_id, score in similarities[:count]:
            rec = ContentRecommendation(
                asset_id=asset_id,
                recommendation_type=RecommendationType.PERSONALIZED,
                score=score,
                confidence=0.7,
                reasons=[
                    RecommendationReason(
                        type="content_based",
                        description="Based on your viewing history",
                        weight=score
                    )
                ],
                model_version=self.model_version
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _collaborative_filtering(
        self,
        user_id: str,
        count: int
    ) -> List[ContentRecommendation]:
        """Collaborative filtering using matrix factorization"""
        # This is a simplified version - in production, use the SVD model
        return []
    
    async def _get_user_index(self, user_id: str) -> Optional[int]:
        """Get user index in matrix"""
        # Implementation would map user_id to matrix index
        return None
    
    async def _get_asset_id_from_index(self, index: int) -> Optional[str]:
        """Get asset ID from matrix index"""
        # Implementation would map matrix index to asset_id
        return None
    
    async def _store_recommendation(self, recommendation: ContentRecommendation, user_id: str):
        """Store recommendation in database"""
        db_rec = ContentRecommendationModel(
            user_id=user_id,
            asset_id=recommendation.asset_id,
            recommendation_type=recommendation.recommendation_type,
            score=recommendation.score,
            confidence=recommendation.confidence,
            reasons=recommendation.reasons,
            model_version=recommendation.model_version
        )
        
        self.db.add(db_rec)
        await self.db.commit()
    
    async def _load_models(self):
        """Load or initialize recommendation models"""
        logger.info("Loading recommendation models")
        
        # In production, load from model storage
        # For now, initialize simple models
        self.svd_model = TruncatedSVD(n_components=50)
    
    async def _periodic_model_update(self):
        """Periodically update recommendation models"""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Daily
                
                logger.info("Updating recommendation models")
                await self._train_collaborative_model()
                
            except Exception as e:
                logger.error("Error updating models", error=str(e))
    
    async def _train_collaborative_model(self):
        """Train collaborative filtering model"""
        # Get user-item interactions
        result = await self.db.execute(
            select(
                UsageHistoryModel.user_id,
                UsageHistoryModel.asset_id,
                func.sum(UsageHistoryModel.access_count)
            )
            .group_by(UsageHistoryModel.user_id, UsageHistoryModel.asset_id)
        )
        
        interactions = result.all()
        
        if len(interactions) < 1000:
            logger.warning("Not enough data for collaborative filtering")
            return
        
        # Create user-item matrix
        # In production, use sparse matrix and more sophisticated techniques
        logger.info(f"Training on {len(interactions)} interactions")