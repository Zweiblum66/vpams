"""
Search Result Ranking Service - Custom ranking algorithms for search results
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from ..models.schemas import SearchHit, RankingConfig, RankingType
from ..core.config import get_settings

logger = structlog.get_logger()


class RankingService:
    """Service for ranking search results based on various factors"""
    
    def __init__(self):
        self.settings = get_settings()
        self.default_config = RankingConfig()
    
    async def rank_results(
        self, 
        hits: List[SearchHit], 
        query: str,
        config: Optional[RankingConfig] = None
    ) -> List[SearchHit]:
        """
        Rank search results based on multiple factors
        
        Args:
            hits: List of search hits to rank
            query: Original search query
            config: Ranking configuration (uses default if not provided)
            
        Returns:
            Sorted list of search hits
        """
        if not hits:
            return hits
        
        config = config or self.default_config
        
        logger.info(
            "ranking_search_results",
            hit_count=len(hits),
            ranking_type=config.ranking_type
        )
        
        # Calculate scores based on ranking type
        if config.ranking_type == RankingType.RELEVANCE:
            ranked_hits = await self._rank_by_relevance(hits, query, config)
        elif config.ranking_type == RankingType.RECENCY:
            ranked_hits = await self._rank_by_recency(hits, config)
        elif config.ranking_type == RankingType.POPULARITY:
            ranked_hits = await self._rank_by_popularity(hits, config)
        elif config.ranking_type == RankingType.CUSTOM:
            ranked_hits = await self._rank_by_custom_score(hits, query, config)
        else:
            # Default to hybrid ranking
            ranked_hits = await self._rank_by_hybrid(hits, query, config)
        
        logger.info(
            "ranking_completed",
            original_order=[h.id for h in hits[:5]],
            new_order=[h.id for h in ranked_hits[:5]]
        )
        
        return ranked_hits
    
    async def _rank_by_relevance(
        self, 
        hits: List[SearchHit], 
        query: str,
        config: RankingConfig
    ) -> List[SearchHit]:
        """Rank purely by search relevance score"""
        # Sort by OpenSearch score (descending)
        return sorted(hits, key=lambda h: h.score, reverse=True)
    
    async def _rank_by_recency(
        self, 
        hits: List[SearchHit],
        config: RankingConfig
    ) -> List[SearchHit]:
        """Rank by how recent the content is"""
        now = datetime.utcnow()
        
        def recency_score(hit: SearchHit) -> float:
            # Get created_at or updated_at timestamp
            created_at_str = hit.source.get('created_at') or hit.source.get('updated_at')
            if not created_at_str:
                return 0.0
            
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                age_days = (now - created_at).days
                
                # Exponential decay based on age
                # Score is 1.0 for today, ~0.5 for 30 days ago, ~0.25 for 60 days
                return math.exp(-age_days / config.recency_decay_days)
            except:
                return 0.0
        
        # Calculate recency scores and sort
        for hit in hits:
            hit._recency_score = recency_score(hit)
        
        return sorted(hits, key=lambda h: h._recency_score, reverse=True)
    
    async def _rank_by_popularity(
        self, 
        hits: List[SearchHit],
        config: RankingConfig
    ) -> List[SearchHit]:
        """Rank by popularity metrics (views, downloads, etc.)"""
        def popularity_score(hit: SearchHit) -> float:
            views = hit.source.get('view_count', 0)
            downloads = hit.source.get('download_count', 0)
            shares = hit.source.get('share_count', 0)
            ratings = hit.source.get('rating', 0)
            rating_count = hit.source.get('rating_count', 1)
            
            # Weighted popularity score
            score = (
                views * config.popularity_weights.get('views', 1.0) +
                downloads * config.popularity_weights.get('downloads', 2.0) +
                shares * config.popularity_weights.get('shares', 3.0) +
                (ratings / 5.0) * rating_count * config.popularity_weights.get('ratings', 1.5)
            )
            
            # Apply logarithmic scaling to prevent extremely popular items from dominating
            return math.log(score + 1)
        
        # Calculate popularity scores and sort
        for hit in hits:
            hit._popularity_score = popularity_score(hit)
        
        return sorted(hits, key=lambda h: h._popularity_score, reverse=True)
    
    async def _rank_by_custom_score(
        self, 
        hits: List[SearchHit],
        query: str,
        config: RankingConfig
    ) -> List[SearchHit]:
        """Rank by custom scoring function"""
        for hit in hits:
            # Initialize custom score components
            score_components = {}
            
            # Field boosts based on where query terms appear
            field_boost_score = self._calculate_field_boost_score(hit, query, config)
            score_components['field_boost'] = field_boost_score
            
            # Asset type preferences
            asset_type_score = self._calculate_asset_type_score(hit, config)
            score_components['asset_type'] = asset_type_score
            
            # Quality indicators
            quality_score = self._calculate_quality_score(hit, config)
            score_components['quality'] = quality_score
            
            # Combine scores
            hit._custom_score = sum(
                score * config.custom_weights.get(name, 1.0)
                for name, score in score_components.items()
            )
            hit._score_components = score_components
        
        return sorted(hits, key=lambda h: h._custom_score, reverse=True)
    
    async def _rank_by_hybrid(
        self, 
        hits: List[SearchHit],
        query: str,
        config: RankingConfig
    ) -> List[SearchHit]:
        """Hybrid ranking combining multiple factors"""
        now = datetime.utcnow()
        
        for hit in hits:
            # Get base relevance score from OpenSearch
            relevance_score = hit.score
            
            # Calculate recency factor
            created_at_str = hit.source.get('created_at') or hit.source.get('updated_at')
            recency_factor = 1.0
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    age_days = (now - created_at).days
                    recency_factor = math.exp(-age_days / config.recency_decay_days)
                except:
                    pass
            
            # Calculate popularity factor
            views = hit.source.get('view_count', 0)
            downloads = hit.source.get('download_count', 0)
            popularity_factor = math.log(views + downloads + 1) / 10.0
            
            # Calculate quality factor
            has_metadata = bool(hit.source.get('metadata', {}))
            has_thumbnail = bool(hit.source.get('thumbnail_path'))
            has_proxies = bool(hit.source.get('proxy_paths'))
            quality_factor = (
                (1.0 if has_metadata else 0.0) +
                (0.5 if has_thumbnail else 0.0) +
                (0.5 if has_proxies else 0.0)
            ) / 2.0
            
            # Combine factors with weights
            hit._hybrid_score = (
                relevance_score * config.hybrid_weights.get('relevance', 1.0) +
                recency_factor * config.hybrid_weights.get('recency', 0.3) +
                popularity_factor * config.hybrid_weights.get('popularity', 0.2) +
                quality_factor * config.hybrid_weights.get('quality', 0.1)
            )
            
            # Store individual factors for debugging
            hit._ranking_factors = {
                'relevance': relevance_score,
                'recency': recency_factor,
                'popularity': popularity_factor,
                'quality': quality_factor,
                'final_score': hit._hybrid_score
            }
        
        return sorted(hits, key=lambda h: h._hybrid_score, reverse=True)
    
    def _calculate_field_boost_score(
        self, 
        hit: SearchHit, 
        query: str,
        config: RankingConfig
    ) -> float:
        """Calculate boost score based on which fields contain query terms"""
        score = 0.0
        query_terms = query.lower().split()
        
        # Check title/name fields
        title = (hit.source.get('title') or hit.source.get('name', '')).lower()
        if any(term in title for term in query_terms):
            score += config.field_boosts.get('title', 2.0)
        
        # Check description
        description = hit.source.get('description', '').lower()
        if any(term in description for term in query_terms):
            score += config.field_boosts.get('description', 1.0)
        
        # Check tags/keywords
        tags = hit.source.get('tags', []) + hit.source.get('keywords', [])
        tags_text = ' '.join(tags).lower()
        if any(term in tags_text for term in query_terms):
            score += config.field_boosts.get('tags', 1.5)
        
        return score
    
    def _calculate_asset_type_score(
        self, 
        hit: SearchHit,
        config: RankingConfig
    ) -> float:
        """Calculate score based on asset type preferences"""
        asset_type = hit.source.get('asset_type', 'unknown')
        return config.asset_type_boosts.get(asset_type, 1.0)
    
    def _calculate_quality_score(
        self, 
        hit: SearchHit,
        config: RankingConfig
    ) -> float:
        """Calculate score based on content quality indicators"""
        score = 0.0
        
        # Has comprehensive metadata
        metadata = hit.source.get('metadata', {})
        if metadata:
            score += 0.2 * min(len(metadata), 10) / 10.0  # Up to 0.2 points
        
        # Has proxies/thumbnails
        if hit.source.get('proxy_paths'):
            score += 0.3
        if hit.source.get('thumbnail_path'):
            score += 0.2
        
        # Has transcription or captions
        if hit.source.get('transcript') or hit.source.get('captions'):
            score += 0.3
        
        # File size indicator (larger files might be higher quality)
        file_size = hit.source.get('file_size', 0)
        if file_size > 100_000_000:  # > 100MB
            score += 0.2
        elif file_size > 10_000_000:  # > 10MB
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def get_ranking_explanation(self, hit: SearchHit) -> Dict[str, Any]:
        """Get explanation of how a hit was ranked"""
        explanation = {
            'original_score': hit.score,
            'id': hit.id,
            'index': hit.index
        }
        
        # Add any ranking factors that were calculated
        if hasattr(hit, '_ranking_factors'):
            explanation['factors'] = hit._ranking_factors
        if hasattr(hit, '_hybrid_score'):
            explanation['hybrid_score'] = hit._hybrid_score
        if hasattr(hit, '_custom_score'):
            explanation['custom_score'] = hit._custom_score
        if hasattr(hit, '_score_components'):
            explanation['score_components'] = hit._score_components
        
        return explanation


async def get_ranking_service() -> RankingService:
    """Get ranking service instance"""
    return RankingService()