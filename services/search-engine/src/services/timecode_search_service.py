"""
Timecode Search Service - Handles timecode-based searches for video and audio assets
"""

import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import structlog
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, ConnectionError as OpenSearchConnectionError

from ..models.schemas import (
    TimecodeSearchQuery, TimecodeSearchResponse, TimecodeSearchResult,
    TimecodeSearchStats, TimecodeValidationResult, TimecodeConversionRequest,
    TimecodeConversionResponse, Timecode, TimecodeRange, TimecodeFormat,
    TimecodeRangeType, TimecodeSearchType, IndexType, SortOrder
)
from ..db.opensearch import get_opensearch_client
from ..core.config import get_settings
from ..core.exceptions import SearchError, ValidationError

logger = structlog.get_logger()


class TimecodeSearchService:
    """Service for handling timecode-based searches"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.settings = get_settings()
        self.index_mappings = {
            IndexType.ASSETS: self.settings.assets_index_name,
            IndexType.METADATA: self.settings.metadata_index_name,
            IndexType.CONTENT: self.settings.content_index_name,
            IndexType.ALL: f"{self.settings.assets_index_name},{self.settings.metadata_index_name},{self.settings.content_index_name}"
        }
    
    async def search_by_timecode(self, query: TimecodeSearchQuery) -> TimecodeSearchResponse:
        """Perform timecode-based search"""
        try:
            start_time = datetime.utcnow()
            
            # Build OpenSearch query
            search_body = await self._build_timecode_query(query)
            
            # Get target indices
            indices = self._get_target_indices(query.indices)
            
            # Execute search
            logger.info("Executing timecode search", 
                       search_type=query.search_type,
                       indices=indices,
                       query_type=type(query).__name__)
            
            response = await self.client.search(
                index=indices,
                body=search_body,
                timeout="30s"
            )
            
            # Process results
            results = await self._process_search_results(response, query)
            
            # Calculate pagination
            total = response['hits']['total']['value']
            pages = (total + query.limit - 1) // query.limit
            
            # Build search response
            search_response = TimecodeSearchResponse(
                results=results,
                total=total,
                took=response['took'],
                page=query.page,
                limit=query.limit,
                pages=pages,
                aggregations=response.get('aggregations', {}),
                search_metadata={
                    'search_type': query.search_type,
                    'indices': query.indices,
                    'execution_time': (datetime.utcnow() - start_time).total_seconds()
                }
            )
            
            # Add statistics if available
            if response.get('aggregations'):
                search_response.duration_stats = response['aggregations'].get('duration_stats')
                search_response.frame_rate_distribution = response['aggregations'].get('frame_rate_distribution')
                search_response.format_distribution = response['aggregations'].get('format_distribution')
            
            logger.info("Timecode search completed", 
                       total_results=total,
                       took_ms=response['took'],
                       search_type=query.search_type)
            
            return search_response
            
        except RequestError as e:
            logger.error("OpenSearch request error in timecode search", error=str(e))
            raise SearchError(f"Invalid timecode search query: {str(e)}")
        except OpenSearchConnectionError as e:
            logger.error("OpenSearch connection error in timecode search", error=str(e))
            raise SearchError("Search service temporarily unavailable")
        except Exception as e:
            logger.error("Unexpected error in timecode search", error=str(e))
            raise SearchError(f"Timecode search failed: {str(e)}")
    
    async def _build_timecode_query(self, query: TimecodeSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query for timecode search"""
        search_body = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [],
                    "should": []
                }
            },
            "size": query.limit,
            "from": (query.page - 1) * query.limit,
            "sort": await self._build_sort_clause(query),
            "aggs": await self._build_aggregations(query)
        }
        
        # Add timecode-specific filters
        await self._add_timecode_filters(search_body, query)
        
        # Add duration filters
        await self._add_duration_filters(search_body, query)
        
        # Add asset type filters
        await self._add_asset_type_filters(search_body, query)
        
        # Add metadata filters
        await self._add_metadata_filters(search_body, query)
        
        # Add search type specific queries
        await self._add_search_type_queries(search_body, query)
        
        # Ensure we have at least one query
        if not search_body["query"]["bool"]["must"] and not search_body["query"]["bool"]["filter"]:
            search_body["query"]["bool"]["must"].append({"match_all": {}})
        
        return search_body
    
    async def _add_timecode_filters(self, search_body: Dict[str, Any], query: TimecodeSearchQuery):
        """Add timecode-specific filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.timecode:
            # Exact timecode search with tolerance
            timecode_seconds = query.timecode.to_seconds()
            tolerance = query.tolerance_seconds
            
            bool_query["filter"].append({
                "range": {
                    "timecode_start": {
                        "gte": timecode_seconds - tolerance,
                        "lte": timecode_seconds + tolerance
                    }
                }
            })
            
            # Add scoring boost for exact matches
            bool_query["should"].append({
                "function_score": {
                    "query": {
                        "range": {
                            "timecode_start": {
                                "gte": timecode_seconds - 0.1,
                                "lte": timecode_seconds + 0.1
                            }
                        }
                    },
                    "boost": 2.0
                }
            })
        
        if query.timecode_range:
            # Range-based timecode search
            range_start = query.timecode_range.start.to_seconds()
            range_end = query.timecode_range.end.to_seconds()
            
            if query.timecode_range.type == TimecodeRangeType.EXACT:
                # Assets that exactly match the range
                bool_query["filter"].extend([
                    {"range": {"timecode_start": {"gte": range_start - query.tolerance_seconds, "lte": range_start + query.tolerance_seconds}}},
                    {"range": {"timecode_end": {"gte": range_end - query.tolerance_seconds, "lte": range_end + query.tolerance_seconds}}}
                ])
            elif query.timecode_range.type == TimecodeRangeType.RANGE:
                # Assets within the range
                bool_query["filter"].append({
                    "range": {
                        "timecode_start": {"gte": range_start, "lte": range_end}
                    }
                })
            elif query.timecode_range.type == TimecodeRangeType.OVERLAP:
                # Assets that overlap with the range
                bool_query["filter"].append({
                    "bool": {
                        "should": [
                            {"range": {"timecode_start": {"gte": range_start, "lte": range_end}}},
                            {"range": {"timecode_end": {"gte": range_start, "lte": range_end}}},
                            {
                                "bool": {
                                    "must": [
                                        {"range": {"timecode_start": {"lte": range_start}}},
                                        {"range": {"timecode_end": {"gte": range_end}}}
                                    ]
                                }
                            }
                        ]
                    }
                })
            elif query.timecode_range.type == TimecodeRangeType.CONTAINS:
                # Assets that contain the range
                bool_query["filter"].extend([
                    {"range": {"timecode_start": {"lte": range_start}}},
                    {"range": {"timecode_end": {"gte": range_end}}}
                ])
            elif query.timecode_range.type == TimecodeRangeType.WITHIN:
                # Assets completely within the range
                bool_query["filter"].extend([
                    {"range": {"timecode_start": {"gte": range_start}}},
                    {"range": {"timecode_end": {"lte": range_end}}}
                ])
    
    async def _add_duration_filters(self, search_body: Dict[str, Any], query: TimecodeSearchQuery):
        """Add duration-based filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.min_duration is not None:
            bool_query["filter"].append({
                "range": {
                    "duration": {"gte": query.min_duration}
                }
            })
        
        if query.max_duration is not None:
            bool_query["filter"].append({
                "range": {
                    "duration": {"lte": query.max_duration}
                }
            })
    
    async def _add_asset_type_filters(self, search_body: Dict[str, Any], query: TimecodeSearchQuery):
        """Add asset type filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.asset_types:
            bool_query["filter"].append({
                "terms": {"asset_type": query.asset_types}
            })
        
        if query.video_formats:
            bool_query["filter"].append({
                "terms": {"video_format": query.video_formats}
            })
        
        if query.audio_formats:
            bool_query["filter"].append({
                "terms": {"audio_format": query.audio_formats}
            })
    
    async def _add_metadata_filters(self, search_body: Dict[str, Any], query: TimecodeSearchQuery):
        """Add metadata filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.frame_rates:
            bool_query["filter"].append({
                "terms": {"frame_rate": query.frame_rates}
            })
        
        if query.resolutions:
            bool_query["filter"].append({
                "terms": {"resolution": query.resolutions}
            })
    
    async def _add_search_type_queries(self, search_body: Dict[str, Any], query: TimecodeSearchQuery):
        """Add search type specific queries"""
        bool_query = search_body["query"]["bool"]
        
        if query.search_type == TimecodeSearchType.SEGMENT:
            # Search for segments within media
            if query.segment_markers:
                bool_query["should"].append({
                    "nested": {
                        "path": "markers",
                        "query": {
                            "terms": {"markers.name": query.segment_markers}
                        }
                    }
                })
            
            if query.chapter_titles:
                bool_query["should"].append({
                    "nested": {
                        "path": "chapters",
                        "query": {
                            "terms": {"chapters.title": query.chapter_titles}
                        }
                    }
                })
        
        elif query.search_type == TimecodeSearchType.SUBTITLE:
            # Search based on subtitle timecodes
            if query.subtitle_text:
                bool_query["should"].append({
                    "nested": {
                        "path": "subtitles",
                        "query": {
                            "bool": {
                                "must": [
                                    {"match": {"subtitles.text": query.subtitle_text}}
                                ],
                                "filter": [
                                    {"term": {"subtitles.language": query.subtitle_language}}
                                ] if query.subtitle_language else []
                            }
                        }
                    }
                })
        
        elif query.search_type == TimecodeSearchType.MARKER:
            # Search based on markers/chapters
            if query.segment_markers:
                bool_query["must"].append({
                    "nested": {
                        "path": "markers",
                        "query": {
                            "terms": {"markers.name": query.segment_markers}
                        }
                    }
                })
    
    async def _build_sort_clause(self, query: TimecodeSearchQuery) -> List[Dict[str, Any]]:
        """Build sort clause for timecode search"""
        sort_clauses = []
        
        if query.sort_by == "relevance":
            sort_clauses.append({"_score": {"order": "desc"}})
        elif query.sort_by == "duration":
            sort_clauses.append({"duration": {"order": query.sort_order}})
        elif query.sort_by == "timecode":
            sort_clauses.append({"timecode_start": {"order": query.sort_order}})
        elif query.sort_by == "frame_rate":
            sort_clauses.append({"frame_rate": {"order": query.sort_order}})
        elif query.sort_by == "created_at":
            sort_clauses.append({"created_at": {"order": query.sort_order}})
        elif query.sort_by == "updated_at":
            sort_clauses.append({"updated_at": {"order": query.sort_order}})
        else:
            # Default sort
            sort_clauses.append({"_score": {"order": "desc"}})
            sort_clauses.append({"created_at": {"order": "desc"}})
        
        return sort_clauses
    
    async def _build_aggregations(self, query: TimecodeSearchQuery) -> Dict[str, Any]:
        """Build aggregations for timecode search"""
        aggregations = {}
        
        # Duration statistics
        aggregations["duration_stats"] = {
            "stats": {"field": "duration"}
        }
        
        # Frame rate distribution
        aggregations["frame_rate_distribution"] = {
            "terms": {"field": "frame_rate", "size": 20}
        }
        
        # Format distribution
        aggregations["format_distribution"] = {
            "terms": {"field": "video_format", "size": 20}
        }
        
        # Asset type distribution
        aggregations["asset_type_distribution"] = {
            "terms": {"field": "asset_type", "size": 10}
        }
        
        # Timecode format distribution
        aggregations["timecode_format_distribution"] = {
            "terms": {"field": "timecode_format", "size": 10}
        }
        
        return aggregations
    
    async def _process_search_results(self, response: Dict[str, Any], query: TimecodeSearchQuery) -> List[TimecodeSearchResult]:
        """Process OpenSearch response into TimecodeSearchResult objects"""
        results = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            # Extract timecode information
            duration = source.get('duration', 0)
            frame_rate = source.get('frame_rate', 30.0)
            timecode_format = TimecodeFormat(source.get('timecode_format', 'non_drop_frame'))
            
            # Convert duration to timecode string
            duration_timecode = str(Timecode.from_seconds(duration, timecode_format))
            
            # Determine match information
            match_info = await self._calculate_match_info(hit, query)
            
            # Extract segment information
            segment_info = await self._extract_segment_info(source, query)
            
            # Extract subtitle information
            subtitle_info = await self._extract_subtitle_info(source, query)
            
            result = TimecodeSearchResult(
                asset_id=source.get('id', hit['_id']),
                asset_name=source.get('name', 'Unknown'),
                asset_type=source.get('asset_type', 'unknown'),
                duration=duration,
                duration_timecode=duration_timecode,
                frame_rate=frame_rate,
                timecode_format=timecode_format,
                matched_timecode=match_info.get('matched_timecode'),
                matched_range=match_info.get('matched_range'),
                match_score=hit['_score'],
                match_type=match_info.get('match_type', 'unknown'),
                segment_title=segment_info.get('title'),
                segment_description=segment_info.get('description'),
                markers=segment_info.get('markers'),
                subtitle_matches=subtitle_info.get('matches'),
                metadata=source.get('metadata', {}),
                created_at=datetime.fromisoformat(source.get('created_at', datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(source.get('updated_at', datetime.utcnow().isoformat()))
            )
            
            results.append(result)
        
        return results
    
    async def _calculate_match_info(self, hit: Dict[str, Any], query: TimecodeSearchQuery) -> Dict[str, Any]:
        """Calculate match information for the search result"""
        source = hit['_source']
        match_info = {}
        
        if query.timecode:
            # Calculate matched timecode
            asset_start = source.get('timecode_start', 0)
            query_seconds = query.timecode.to_seconds()
            
            if abs(asset_start - query_seconds) <= query.tolerance_seconds:
                match_info['matched_timecode'] = str(query.timecode)
                match_info['match_type'] = 'exact_timecode'
            else:
                match_info['match_type'] = 'approximate_timecode'
        
        elif query.timecode_range:
            # Calculate matched range
            range_start = query.timecode_range.start.to_seconds()
            range_end = query.timecode_range.end.to_seconds()
            
            match_info['matched_range'] = {
                'start': str(query.timecode_range.start),
                'end': str(query.timecode_range.end),
                'type': query.timecode_range.type
            }
            match_info['match_type'] = f'range_{query.timecode_range.type}'
        
        elif query.min_duration or query.max_duration:
            match_info['match_type'] = 'duration'
        
        else:
            match_info['match_type'] = 'metadata'
        
        return match_info
    
    async def _extract_segment_info(self, source: Dict[str, Any], query: TimecodeSearchQuery) -> Dict[str, Any]:
        """Extract segment information from search result"""
        segment_info = {}
        
        if query.search_type == TimecodeSearchType.SEGMENT:
            markers = source.get('markers', [])
            chapters = source.get('chapters', [])
            
            if markers:
                segment_info['markers'] = markers
            
            if chapters:
                for chapter in chapters:
                    if query.chapter_titles and chapter.get('title') in query.chapter_titles:
                        segment_info['title'] = chapter.get('title')
                        segment_info['description'] = chapter.get('description')
                        break
        
        return segment_info
    
    async def _extract_subtitle_info(self, source: Dict[str, Any], query: TimecodeSearchQuery) -> Dict[str, Any]:
        """Extract subtitle information from search result"""
        subtitle_info = {}
        
        if query.search_type == TimecodeSearchType.SUBTITLE and query.subtitle_text:
            subtitles = source.get('subtitles', [])
            matches = []
            
            for subtitle in subtitles:
                if query.subtitle_text.lower() in subtitle.get('text', '').lower():
                    if not query.subtitle_language or subtitle.get('language') == query.subtitle_language:
                        matches.append({
                            'text': subtitle.get('text'),
                            'start_time': subtitle.get('start_time'),
                            'end_time': subtitle.get('end_time'),
                            'language': subtitle.get('language')
                        })
            
            if matches:
                subtitle_info['matches'] = matches
        
        return subtitle_info
    
    def _get_target_indices(self, indices: List[IndexType]) -> str:
        """Get target indices for search"""
        if IndexType.ALL in indices:
            return self.index_mappings[IndexType.ALL]
        
        index_names = []
        for index_type in indices:
            if index_type in self.index_mappings:
                index_names.append(self.index_mappings[index_type])
        
        return ','.join(index_names) if index_names else self.index_mappings[IndexType.ASSETS]
    
    async def validate_timecode(self, timecode_str: str, format: TimecodeFormat = TimecodeFormat.NON_DROP_FRAME) -> TimecodeValidationResult:
        """Validate timecode string"""
        try:
            errors = []
            warnings = []
            
            # Basic format validation
            if not re.match(r'^\d{2}[;:]\d{2}[;:]\d{2}[;:]\d{2}$', timecode_str):
                errors.append("Timecode must be in HH:MM:SS:FF or HH:MM:SS;FF format")
                return TimecodeValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings
                )
            
            # Parse timecode
            timecode = Timecode.from_string(timecode_str, format)
            
            # Validate frame rate compatibility
            if ";" in timecode_str and format != TimecodeFormat.DROP_FRAME:
                warnings.append("Semicolon separator detected but format is not drop frame")
            
            # Validate frame values
            if timecode.frames >= 30 and format in [TimecodeFormat.FILM, TimecodeFormat.PAL]:
                errors.append(f"Frame value {timecode.frames} is invalid for {format} format")
            
            # Calculate normalized values
            total_seconds = timecode.to_seconds()
            total_frames = timecode.to_frames()
            
            return TimecodeValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                normalized_timecode=str(timecode),
                total_seconds=total_seconds,
                total_frames=total_frames,
                detected_format=TimecodeFormat.DROP_FRAME if ";" in timecode_str else format,
                suggested_format=format
            )
            
        except Exception as e:
            return TimecodeValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[]
            )
    
    async def convert_timecode(self, request: TimecodeConversionRequest) -> TimecodeConversionResponse:
        """Convert timecode between formats"""
        try:
            # Parse source timecode
            source_timecode = Timecode.from_string(request.source_timecode, request.source_format)
            
            # Convert to target format
            target_timecode = Timecode.from_seconds(
                source_timecode.to_seconds(), 
                request.target_format
            )
            
            # Check for precision loss
            precision_loss = False
            warnings = []
            
            if request.source_format != request.target_format:
                # Different frame rates may cause precision loss
                source_fps = self._get_frame_rate(request.source_format)
                target_fps = self._get_frame_rate(request.target_format)
                
                if source_fps != target_fps:
                    precision_loss = True
                    warnings.append(f"Precision loss possible when converting from {source_fps}fps to {target_fps}fps")
            
            return TimecodeConversionResponse(
                source_timecode=request.source_timecode,
                target_timecode=str(target_timecode),
                source_format=request.source_format,
                target_format=request.target_format,
                source_seconds=source_timecode.to_seconds(),
                target_seconds=target_timecode.to_seconds(),
                source_frames=source_timecode.to_frames(),
                target_frames=target_timecode.to_frames(),
                conversion_method="frame_rate_conversion",
                precision_loss=precision_loss,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error("Timecode conversion failed", error=str(e))
            raise ValidationError(f"Timecode conversion failed: {str(e)}")
    
    def _get_frame_rate(self, format: TimecodeFormat) -> float:
        """Get frame rate for timecode format"""
        frame_rate_map = {
            TimecodeFormat.FILM: 24.0,
            TimecodeFormat.PAL: 25.0,
            TimecodeFormat.NTSC: 29.97,
            TimecodeFormat.DROP_FRAME: 29.97,
            TimecodeFormat.NON_DROP_FRAME: 30.0
        }
        return frame_rate_map.get(format, 30.0)
    
    async def get_timecode_stats(self) -> TimecodeSearchStats:
        """Get timecode search statistics"""
        try:
            # Query for basic statistics
            stats_query = {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"exists": {"field": "duration"}}
                        ]
                    }
                },
                "aggs": {
                    "duration_stats": {
                        "stats": {"field": "duration"}
                    },
                    "frame_rate_distribution": {
                        "terms": {"field": "frame_rate", "size": 20}
                    },
                    "format_distribution": {
                        "terms": {"field": "timecode_format", "size": 10}
                    }
                }
            }
            
            response = await self.client.search(
                index=self.index_mappings[IndexType.ASSETS],
                body=stats_query
            )
            
            # Extract statistics
            duration_stats = response['aggregations']['duration_stats']
            frame_rate_agg = response['aggregations']['frame_rate_distribution']
            format_agg = response['aggregations']['format_distribution']
            
            # Build frame rate distribution
            frame_rate_distribution = {}
            most_common_frame_rate = 30.0
            if frame_rate_agg['buckets']:
                for bucket in frame_rate_agg['buckets']:
                    frame_rate_distribution[str(bucket['key'])] = bucket['doc_count']
                most_common_frame_rate = float(frame_rate_agg['buckets'][0]['key'])
            
            # Build format distribution
            format_distribution = {}
            most_common_format = TimecodeFormat.NON_DROP_FRAME
            if format_agg['buckets']:
                for bucket in format_agg['buckets']:
                    format_distribution[bucket['key']] = bucket['doc_count']
                most_common_format = TimecodeFormat(format_agg['buckets'][0]['key'])
            
            return TimecodeSearchStats(
                total_searches=0,  # Would need to track this separately
                total_assets_with_timecode=response['hits']['total']['value'],
                avg_duration=duration_stats.get('avg', 0),
                min_duration=duration_stats.get('min', 0),
                max_duration=duration_stats.get('max', 0),
                frame_rate_distribution=frame_rate_distribution,
                most_common_frame_rate=most_common_frame_rate,
                format_distribution=format_distribution,
                most_common_format=most_common_format,
                avg_search_time_ms=0,  # Would need to track this separately
                cache_hit_rate=0  # Would need to track this separately
            )
            
        except Exception as e:
            logger.error("Failed to get timecode stats", error=str(e))
            raise SearchError(f"Failed to get timecode statistics: {str(e)}")


# Service instance
_timecode_search_service: Optional[TimecodeSearchService] = None


async def get_timecode_search_service() -> TimecodeSearchService:
    """Get timecode search service instance"""
    global _timecode_search_service
    
    if _timecode_search_service is None:
        opensearch_client = await get_opensearch_client()
        _timecode_search_service = TimecodeSearchService(opensearch_client)
    
    return _timecode_search_service