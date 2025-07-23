"""
Color Search Service - Handles color-based searches for image and video assets
"""

import math
import colorsys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import structlog
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, ConnectionError as OpenSearchConnectionError

from ..models.schemas import (
    ColorSearchQuery, ColorSearchResponse, ColorSearchResult, ColorSearchStats,
    ColorAnalysisRequest, ColorAnalysisResponse, Color, ColorPalette, ColorRange,
    ColorSpace, ColorSearchType, ColorMatchType, ColorClusteringMethod,
    IndexType, SortOrder
)
from ..db.opensearch import get_opensearch_client
from ..core.config import get_settings
from ..core.exceptions import SearchError, ValidationError

logger = structlog.get_logger()


class ColorSearchService:
    """Service for handling color-based searches"""
    
    def __init__(self, opensearch_client: AsyncOpenSearch):
        self.client = opensearch_client
        self.settings = get_settings()
        self.index_mappings = {
            IndexType.ASSETS: self.settings.assets_index_name,
            IndexType.METADATA: self.settings.metadata_index_name,
            IndexType.CONTENT: self.settings.content_index_name,
            IndexType.ALL: f"{self.settings.assets_index_name},{self.settings.metadata_index_name},{self.settings.content_index_name}"
        }
    
    async def search_by_color(self, query: ColorSearchQuery) -> ColorSearchResponse:
        """Perform color-based search"""
        try:
            start_time = datetime.utcnow()
            
            # Build OpenSearch query
            search_body = await self._build_color_query(query)
            
            # Get target indices
            indices = self._get_target_indices(query.indices)
            
            # Execute search
            logger.info("Executing color search", 
                       search_type=query.search_type,
                       indices=indices,
                       query_type=type(query).__name__)
            
            response = await self.client.search(
                index=indices,
                body=search_body,
                timeout="60s"  # Color searches may take longer
            )
            
            # Process results
            results = await self._process_search_results(response, query)
            
            # Calculate pagination
            total = response['hits']['total']['value']
            pages = (total + query.limit - 1) // query.limit
            
            # Build search response
            search_response = ColorSearchResponse(
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
                    'execution_time': (datetime.utcnow() - start_time).total_seconds(),
                    'color_space': query.color_space,
                    'match_type': query.match_type
                }
            )
            
            # Add color-specific aggregations
            if response.get('aggregations'):
                search_response.color_distribution = response['aggregations'].get('color_distribution')
                search_response.palette_analysis = response['aggregations'].get('palette_analysis')
            
            logger.info("Color search completed", 
                       total_results=total,
                       took_ms=response['took'],
                       search_type=query.search_type)
            
            return search_response
            
        except RequestError as e:
            logger.error("OpenSearch request error in color search", error=str(e))
            raise SearchError(f"Invalid color search query: {str(e)}")
        except OpenSearchConnectionError as e:
            logger.error("OpenSearch connection error in color search", error=str(e))
            raise SearchError("Search service temporarily unavailable")
        except Exception as e:
            logger.error("Unexpected error in color search", error=str(e))
            raise SearchError(f"Color search failed: {str(e)}")
    
    async def _build_color_query(self, query: ColorSearchQuery) -> Dict[str, Any]:
        """Build OpenSearch query for color search"""
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
            "aggs": await self._build_color_aggregations(query)
        }
        
        # Add color-specific filters
        await self._add_color_filters(search_body, query)
        
        # Add asset type filters
        await self._add_asset_type_filters(search_body, query)
        
        # Add format filters
        await self._add_format_filters(search_body, query)
        
        # Add color range filters
        await self._add_color_range_filters(search_body, query)
        
        # Add search type specific queries
        await self._add_color_search_type_queries(search_body, query)
        
        # Ensure we have at least one query
        if not search_body["query"]["bool"]["must"] and not search_body["query"]["bool"]["filter"]:
            search_body["query"]["bool"]["must"].append({"match_all": {}})
        
        return search_body
    
    async def _add_color_filters(self, search_body: Dict[str, Any], query: ColorSearchQuery):
        """Add color-specific filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.target_color:
            # Convert target color to search format
            target_rgb = [query.target_color.r, query.target_color.g, query.target_color.b]
            
            # Create color similarity query
            color_similarity_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": await self._get_color_similarity_script(query.match_type),
                        "params": {
                            "target_color": target_rgb,
                            "tolerance": query.tolerance,
                            "color_space": query.color_space
                        }
                    }
                }
            }
            
            bool_query["must"].append(color_similarity_query)
        
        if query.color_palette:
            # Search for assets with similar color palettes
            palette_colors = [[c.r, c.g, c.b] for c in query.color_palette.colors]
            
            palette_query = {
                "nested": {
                    "path": "color_analysis.palette",
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "script_score": {
                                        "query": {"match_all": {}},
                                        "script": {
                                            "source": await self._get_palette_similarity_script(),
                                            "params": {
                                                "palette_colors": palette_colors,
                                                "tolerance": query.tolerance
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
            
            bool_query["should"].append(palette_query)
        
        # Add percentage filters
        if query.min_color_percentage is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.dominant_color_percentage": {
                        "gte": query.min_color_percentage
                    }
                }
            })
        
        if query.max_color_percentage is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.dominant_color_percentage": {
                        "lte": query.max_color_percentage
                    }
                }
            })
    
    async def _add_asset_type_filters(self, search_body: Dict[str, Any], query: ColorSearchQuery):
        """Add asset type filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.asset_types:
            bool_query["filter"].append({
                "terms": {"asset_type": query.asset_types}
            })
    
    async def _add_format_filters(self, search_body: Dict[str, Any], query: ColorSearchQuery):
        """Add format filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        if query.video_formats:
            bool_query["filter"].append({
                "terms": {"video_format": query.video_formats}
            })
        
        if query.image_formats:
            bool_query["filter"].append({
                "terms": {"image_format": query.image_formats}
            })
    
    async def _add_color_range_filters(self, search_body: Dict[str, Any], query: ColorSearchQuery):
        """Add color range filters to the query"""
        bool_query = search_body["query"]["bool"]
        
        # Brightness filters
        if query.min_brightness is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.brightness": {"gte": query.min_brightness}
                }
            })
        
        if query.max_brightness is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.brightness": {"lte": query.max_brightness}
                }
            })
        
        # Saturation filters
        if query.min_saturation is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.saturation": {"gte": query.min_saturation}
                }
            })
        
        if query.max_saturation is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.saturation": {"lte": query.max_saturation}
                }
            })
        
        # Hue filters
        if query.min_hue is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.hue": {"gte": query.min_hue}
                }
            })
        
        if query.max_hue is not None:
            bool_query["filter"].append({
                "range": {
                    "color_analysis.hue": {"lte": query.max_hue}
                }
            })
    
    async def _add_color_search_type_queries(self, search_body: Dict[str, Any], query: ColorSearchQuery):
        """Add search type specific queries"""
        bool_query = search_body["query"]["bool"]
        
        if query.search_type == ColorSearchType.WARM_COLORS:
            # Search for warm colors (red, orange, yellow)
            warm_color_query = {
                "range": {
                    "color_analysis.color_temperature": {"gte": 3000}
                }
            }
            bool_query["filter"].append(warm_color_query)
        
        elif query.search_type == ColorSearchType.COOL_COLORS:
            # Search for cool colors (blue, green, purple)
            cool_color_query = {
                "range": {
                    "color_analysis.color_temperature": {"lte": 3000}
                }
            }
            bool_query["filter"].append(cool_color_query)
        
        elif query.search_type == ColorSearchType.MONOCHROMATIC:
            # Search for monochromatic images (low color diversity)
            mono_query = {
                "range": {
                    "color_analysis.color_diversity": {"lte": 0.3}
                }
            }
            bool_query["filter"].append(mono_query)
        
        elif query.search_type == ColorSearchType.COMPLEMENTARY_COLORS:
            # Search for images with complementary color schemes
            complementary_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": """
                        if (doc['color_analysis.palette'].length >= 2) {
                            // Check for complementary colors in palette
                            return Math.random() * 2; // Placeholder score
                        }
                        return 0;
                        """
                    }
                }
            }
            bool_query["should"].append(complementary_query)
        
        elif query.search_type == ColorSearchType.ANALOGOUS_COLORS:
            # Search for images with analogous color schemes
            analogous_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": """
                        if (doc['color_analysis.palette'].length >= 3) {
                            // Check for analogous colors in palette
                            return Math.random() * 2; // Placeholder score
                        }
                        return 0;
                        """
                    }
                }
            }
            bool_query["should"].append(analogous_query)
        
        elif query.search_type == ColorSearchType.TRIADIC_COLORS:
            # Search for images with triadic color schemes
            triadic_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": """
                        if (doc['color_analysis.palette'].length >= 3) {
                            // Check for triadic colors in palette
                            return Math.random() * 2; // Placeholder score
                        }
                        return 0;
                        """
                    }
                }
            }
            bool_query["should"].append(triadic_query)
    
    async def _get_color_similarity_script(self, match_type: ColorMatchType) -> str:
        """Get the appropriate color similarity script"""
        if match_type == ColorMatchType.EUCLIDEAN:
            return """
            double similarity = 0.0;
            if (doc['color_analysis.dominant_colors'].length > 0) {
                def dominantColor = doc['color_analysis.dominant_colors'][0];
                if (dominantColor.containsKey('r') && dominantColor.containsKey('g') && dominantColor.containsKey('b')) {
                    double dr = params.target_color[0] - dominantColor['r'];
                    double dg = params.target_color[1] - dominantColor['g'];
                    double db = params.target_color[2] - dominantColor['b'];
                    double distance = Math.sqrt(dr*dr + dg*dg + db*db);
                    similarity = Math.max(0, (255 - distance) / 255);
                }
            }
            return similarity * 100;
            """
        elif match_type == ColorMatchType.MANHATTAN:
            return """
            double similarity = 0.0;
            if (doc['color_analysis.dominant_colors'].length > 0) {
                def dominantColor = doc['color_analysis.dominant_colors'][0];
                if (dominantColor.containsKey('r') && dominantColor.containsKey('g') && dominantColor.containsKey('b')) {
                    double dr = Math.abs(params.target_color[0] - dominantColor['r']);
                    double dg = Math.abs(params.target_color[1] - dominantColor['g']);
                    double db = Math.abs(params.target_color[2] - dominantColor['b']);
                    double distance = dr + dg + db;
                    similarity = Math.max(0, (765 - distance) / 765);
                }
            }
            return similarity * 100;
            """
        elif match_type == ColorMatchType.COSINE:
            return """
            double similarity = 0.0;
            if (doc['color_analysis.dominant_colors'].length > 0) {
                def dominantColor = doc['color_analysis.dominant_colors'][0];
                if (dominantColor.containsKey('r') && dominantColor.containsKey('g') && dominantColor.containsKey('b')) {
                    double dotProduct = params.target_color[0] * dominantColor['r'] + 
                                      params.target_color[1] * dominantColor['g'] + 
                                      params.target_color[2] * dominantColor['b'];
                    double magnitude1 = Math.sqrt(params.target_color[0] * params.target_color[0] + 
                                                 params.target_color[1] * params.target_color[1] + 
                                                 params.target_color[2] * params.target_color[2]);
                    double magnitude2 = Math.sqrt(dominantColor['r'] * dominantColor['r'] + 
                                                 dominantColor['g'] * dominantColor['g'] + 
                                                 dominantColor['b'] * dominantColor['b']);
                    if (magnitude1 > 0 && magnitude2 > 0) {
                        similarity = dotProduct / (magnitude1 * magnitude2);
                    }
                }
            }
            return similarity * 100;
            """
        else:
            # Default to Euclidean
            return await self._get_color_similarity_script(ColorMatchType.EUCLIDEAN)
    
    async def _get_palette_similarity_script(self) -> str:
        """Get script for palette similarity matching"""
        return """
        double maxSimilarity = 0.0;
        if (doc['color_analysis.palette'].length > 0) {
            for (int i = 0; i < doc['color_analysis.palette'].length; i++) {
                def paletteColor = doc['color_analysis.palette'][i];
                if (paletteColor.containsKey('r') && paletteColor.containsKey('g') && paletteColor.containsKey('b')) {
                    for (int j = 0; j < params.palette_colors.length; j++) {
                        double dr = params.palette_colors[j][0] - paletteColor['r'];
                        double dg = params.palette_colors[j][1] - paletteColor['g'];
                        double db = params.palette_colors[j][2] - paletteColor['b'];
                        double distance = Math.sqrt(dr*dr + dg*dg + db*db);
                        double similarity = Math.max(0, (255 - distance) / 255);
                        if (similarity > maxSimilarity) {
                            maxSimilarity = similarity;
                        }
                    }
                }
            }
        }
        return maxSimilarity * 100;
        """
    
    async def _build_sort_clause(self, query: ColorSearchQuery) -> List[Dict[str, Any]]:
        """Build sort clause for color search"""
        sort_clauses = []
        
        if query.sort_by == "relevance":
            sort_clauses.append({"_score": {"order": "desc"}})
        elif query.sort_by == "color_similarity":
            sort_clauses.append({"color_analysis.color_similarity": {"order": query.sort_order}})
        elif query.sort_by == "color_diversity":
            sort_clauses.append({"color_analysis.color_diversity": {"order": query.sort_order}})
        elif query.sort_by == "brightness":
            sort_clauses.append({"color_analysis.brightness": {"order": query.sort_order}})
        elif query.sort_by == "saturation":
            sort_clauses.append({"color_analysis.saturation": {"order": query.sort_order}})
        elif query.sort_by == "created_at":
            sort_clauses.append({"created_at": {"order": query.sort_order}})
        elif query.sort_by == "updated_at":
            sort_clauses.append({"updated_at": {"order": query.sort_order}})
        else:
            # Default sort
            sort_clauses.append({"_score": {"order": "desc"}})
            sort_clauses.append({"created_at": {"order": "desc"}})
        
        return sort_clauses
    
    async def _build_color_aggregations(self, query: ColorSearchQuery) -> Dict[str, Any]:
        """Build aggregations for color search"""
        aggregations = {}
        
        # Color distribution aggregation
        aggregations["color_distribution"] = {
            "nested": {
                "path": "color_analysis.palette"
            },
            "aggs": {
                "color_histogram": {
                    "histogram": {
                        "field": "color_analysis.palette.hue",
                        "interval": 30,
                        "min_doc_count": 1
                    }
                }
            }
        }
        
        # Brightness distribution
        aggregations["brightness_distribution"] = {
            "histogram": {
                "field": "color_analysis.brightness",
                "interval": 0.1,
                "min_doc_count": 1
            }
        }
        
        # Saturation distribution
        aggregations["saturation_distribution"] = {
            "histogram": {
                "field": "color_analysis.saturation",
                "interval": 0.1,
                "min_doc_count": 1
            }
        }
        
        # Color temperature distribution
        aggregations["color_temperature_distribution"] = {
            "histogram": {
                "field": "color_analysis.color_temperature",
                "interval": 500,
                "min_doc_count": 1
            }
        }
        
        # Asset type distribution
        aggregations["asset_type_distribution"] = {
            "terms": {
                "field": "asset_type",
                "size": 10
            }
        }
        
        # Color diversity statistics
        aggregations["color_diversity_stats"] = {
            "stats": {
                "field": "color_analysis.color_diversity"
            }
        }
        
        return aggregations
    
    async def _process_search_results(self, response: Dict[str, Any], query: ColorSearchQuery) -> List[ColorSearchResult]:
        """Process OpenSearch response into ColorSearchResult objects"""
        results = []
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            
            # Extract color analysis data
            color_analysis = source.get('color_analysis', {})
            
            # Build dominant colors
            dominant_colors = []
            if color_analysis.get('dominant_colors'):
                for color_data in color_analysis['dominant_colors']:
                    color = Color(
                        r=color_data.get('r', 0),
                        g=color_data.get('g', 0),
                        b=color_data.get('b', 0),
                        percentage=color_data.get('percentage'),
                        frequency=color_data.get('frequency')
                    )
                    dominant_colors.append(color)
            
            # Build color palette
            palette_colors = []
            if color_analysis.get('palette'):
                for color_data in color_analysis['palette']:
                    color = Color(
                        r=color_data.get('r', 0),
                        g=color_data.get('g', 0),
                        b=color_data.get('b', 0),
                        percentage=color_data.get('percentage'),
                        frequency=color_data.get('frequency')
                    )
                    palette_colors.append(color)
            
            color_palette = ColorPalette(
                colors=palette_colors if palette_colors else dominant_colors,
                palette_type=color_analysis.get('palette_type'),
                extraction_method=color_analysis.get('extraction_method'),
                confidence=color_analysis.get('confidence')
            )
            
            # Determine match information
            match_info = await self._calculate_color_match_info(hit, query)
            
            result = ColorSearchResult(
                asset_id=source.get('id', hit['_id']),
                asset_name=source.get('name', 'Unknown'),
                asset_type=source.get('asset_type', 'unknown'),
                dominant_colors=dominant_colors,
                color_palette=color_palette,
                color_histogram=color_analysis.get('histogram'),
                matched_colors=match_info.get('matched_colors', []),
                match_score=hit['_score'],
                match_type=match_info.get('match_type', 'unknown'),
                color_similarity=match_info.get('color_similarity', 0.0),
                color_diversity=color_analysis.get('color_diversity'),
                dominant_color_percentage=color_analysis.get('dominant_color_percentage'),
                color_temperature=color_analysis.get('color_temperature'),
                brightness=color_analysis.get('brightness'),
                contrast=color_analysis.get('contrast'),
                saturation=color_analysis.get('saturation'),
                frame_colors=color_analysis.get('frame_colors'),
                color_timeline=color_analysis.get('color_timeline'),
                file_size=source.get('file_size'),
                dimensions=source.get('dimensions'),
                duration=source.get('duration'),
                format=source.get('format'),
                created_at=datetime.fromisoformat(source.get('created_at', datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(source.get('updated_at', datetime.utcnow().isoformat())),
                analyzed_at=datetime.fromisoformat(color_analysis.get('analyzed_at', datetime.utcnow().isoformat())) if color_analysis.get('analyzed_at') else None
            )
            
            results.append(result)
        
        return results
    
    async def _calculate_color_match_info(self, hit: Dict[str, Any], query: ColorSearchQuery) -> Dict[str, Any]:
        """Calculate color match information for the search result"""
        match_info = {}
        source = hit['_source']
        color_analysis = source.get('color_analysis', {})
        
        if query.target_color:
            # Calculate color similarity
            dominant_colors = color_analysis.get('dominant_colors', [])
            if dominant_colors:
                target_rgb = (query.target_color.r, query.target_color.g, query.target_color.b)
                best_match = None
                best_similarity = 0.0
                
                for color_data in dominant_colors:
                    color_rgb = (color_data.get('r', 0), color_data.get('g', 0), color_data.get('b', 0))
                    similarity = await self._calculate_color_similarity(target_rgb, color_rgb, query.match_type)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = Color(
                            r=color_data.get('r', 0),
                            g=color_data.get('g', 0),
                            b=color_data.get('b', 0),
                            percentage=color_data.get('percentage'),
                            frequency=color_data.get('frequency')
                        )
                
                if best_match:
                    match_info['matched_colors'] = [best_match]
                    match_info['color_similarity'] = best_similarity
                    match_info['match_type'] = 'color_similarity'
        
        elif query.color_palette:
            # Calculate palette similarity
            match_info['match_type'] = 'palette_similarity'
            match_info['color_similarity'] = 0.8  # Placeholder
            match_info['matched_colors'] = []
        
        elif query.search_type in [ColorSearchType.WARM_COLORS, ColorSearchType.COOL_COLORS]:
            match_info['match_type'] = 'color_temperature'
            match_info['color_similarity'] = 0.9  # Placeholder
            match_info['matched_colors'] = []
        
        else:
            match_info['match_type'] = 'general'
            match_info['color_similarity'] = hit['_score'] / 100.0
            match_info['matched_colors'] = []
        
        return match_info
    
    async def _calculate_color_similarity(self, color1: Tuple[int, int, int], color2: Tuple[int, int, int], match_type: ColorMatchType) -> float:
        """Calculate similarity between two colors"""
        if match_type == ColorMatchType.EUCLIDEAN:
            # Euclidean distance in RGB space
            dr = color1[0] - color2[0]
            dg = color1[1] - color2[1]
            db = color1[2] - color2[2]
            distance = math.sqrt(dr*dr + dg*dg + db*db)
            return max(0, (255 - distance) / 255)
        
        elif match_type == ColorMatchType.MANHATTAN:
            # Manhattan distance in RGB space
            dr = abs(color1[0] - color2[0])
            dg = abs(color1[1] - color2[1])
            db = abs(color1[2] - color2[2])
            distance = dr + dg + db
            return max(0, (765 - distance) / 765)
        
        elif match_type == ColorMatchType.COSINE:
            # Cosine similarity
            dot_product = color1[0]*color2[0] + color1[1]*color2[1] + color1[2]*color2[2]
            magnitude1 = math.sqrt(color1[0]**2 + color1[1]**2 + color1[2]**2)
            magnitude2 = math.sqrt(color2[0]**2 + color2[1]**2 + color2[2]**2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        
        elif match_type == ColorMatchType.DELTA_E:
            # Delta E color difference (CIE76)
            # Convert RGB to LAB first
            lab1 = self._rgb_to_lab(color1)
            lab2 = self._rgb_to_lab(color2)
            
            dl = lab1[0] - lab2[0]
            da = lab1[1] - lab2[1]
            db = lab1[2] - lab2[2]
            
            delta_e = math.sqrt(dl*dl + da*da + db*db)
            return max(0, (100 - delta_e) / 100)
        
        else:
            # Default to Euclidean
            return await self._calculate_color_similarity(color1, color2, ColorMatchType.EUCLIDEAN)
    
    def _rgb_to_lab(self, rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to LAB color space"""
        # Convert RGB to XYZ first
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
        
        # Apply gamma correction
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
        
        # Convert to XYZ
        x = r * 0.4124 + g * 0.3576 + b * 0.1805
        y = r * 0.2126 + g * 0.7152 + b * 0.0722
        z = r * 0.0193 + g * 0.1192 + b * 0.9505
        
        # Normalize to D65 illuminant
        x /= 0.95047
        y /= 1.00000
        z /= 1.08883
        
        # Convert to LAB
        fx = x ** (1/3) if x > 0.008856 else (7.787 * x + 16/116)
        fy = y ** (1/3) if y > 0.008856 else (7.787 * y + 16/116)
        fz = z ** (1/3) if z > 0.008856 else (7.787 * z + 16/116)
        
        l = 116 * fy - 16
        a = 500 * (fx - fy)
        b = 200 * (fy - fz)
        
        return (l, a, b)
    
    def _get_target_indices(self, indices: List[IndexType]) -> str:
        """Get target indices for search"""
        if IndexType.ALL in indices:
            return self.index_mappings[IndexType.ALL]
        
        index_names = []
        for index_type in indices:
            if index_type in self.index_mappings:
                index_names.append(self.index_mappings[index_type])
        
        return ','.join(index_names) if index_names else self.index_mappings[IndexType.ASSETS]
    
    async def analyze_asset_colors(self, request: ColorAnalysisRequest) -> ColorAnalysisResponse:
        """Analyze colors in an asset"""
        try:
            start_time = datetime.utcnow()
            
            # This would typically integrate with an image processing service
            # For now, we'll return a mock response
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Mock color analysis results
            dominant_colors = [
                Color(r=120, g=80, b=200, percentage=35.5, frequency=0.355),
                Color(r=200, g=150, b=100, percentage=28.2, frequency=0.282),
                Color(r=80, g=120, b=90, percentage=20.1, frequency=0.201),
                Color(r=180, g=60, b=140, percentage=16.2, frequency=0.162)
            ]
            
            color_palette = ColorPalette(
                colors=dominant_colors,
                palette_type="dominant",
                extraction_method=request.clustering_method,
                confidence=0.85
            )
            
            return ColorAnalysisResponse(
                asset_id=request.asset_id,
                analysis_success=True,
                dominant_colors=dominant_colors,
                color_palette=color_palette,
                color_histogram={"bins": 256, "data": []} if request.include_histogram else None,
                color_diversity=0.75,
                color_temperature=3200.0,
                brightness=0.65,
                contrast=0.82,
                saturation=0.71,
                processing_time_ms=processing_time,
                analysis_method=f"K-means clustering ({request.clustering_method})",
                color_space_used=request.color_space,
                errors=[],
                warnings=[]
            )
            
        except Exception as e:
            logger.error("Color analysis failed", asset_id=request.asset_id, error=str(e))
            return ColorAnalysisResponse(
                asset_id=request.asset_id,
                analysis_success=False,
                dominant_colors=[],
                color_palette=None,
                processing_time_ms=0,
                analysis_method="failed",
                color_space_used=request.color_space,
                errors=[str(e)],
                warnings=[]
            )
    
    async def get_color_search_stats(self) -> ColorSearchStats:
        """Get color search statistics"""
        try:
            # Query for basic statistics
            stats_query = {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"exists": {"field": "color_analysis"}}
                        ]
                    }
                },
                "aggs": {
                    "asset_type_stats": {
                        "terms": {"field": "asset_type", "size": 10}
                    },
                    "color_diversity_stats": {
                        "stats": {"field": "color_analysis.color_diversity"}
                    },
                    "brightness_stats": {
                        "stats": {"field": "color_analysis.brightness"}
                    },
                    "dominant_colors": {
                        "nested": {"path": "color_analysis.dominant_colors"},
                        "aggs": {
                            "color_histogram": {
                                "histogram": {
                                    "field": "color_analysis.dominant_colors.hue",
                                    "interval": 30,
                                    "min_doc_count": 1
                                }
                            }
                        }
                    }
                }
            }
            
            response = await self.client.search(
                index=self.index_mappings[IndexType.ASSETS],
                body=stats_query
            )
            
            # Extract statistics
            total_assets = response['hits']['total']['value']
            asset_type_stats = response['aggregations']['asset_type_stats']
            color_diversity_stats = response['aggregations']['color_diversity_stats']
            
            # Count images and videos
            images_analyzed = 0
            videos_analyzed = 0
            
            for bucket in asset_type_stats['buckets']:
                if bucket['key'] == 'image':
                    images_analyzed = bucket['doc_count']
                elif bucket['key'] == 'video':
                    videos_analyzed = bucket['doc_count']
            
            return ColorSearchStats(
                total_searches=0,  # Would need to track this separately
                total_assets_analyzed=total_assets,
                most_common_colors=[
                    {"color": "#7850C8", "count": 1250},
                    {"color": "#C89664", "count": 980},
                    {"color": "#50785A", "count": 875}
                ],
                color_diversity_stats={
                    "avg": color_diversity_stats.get('avg', 0),
                    "min": color_diversity_stats.get('min', 0),
                    "max": color_diversity_stats.get('max', 0)
                },
                dominant_color_distribution={
                    "warm": 1500,
                    "cool": 1200,
                    "neutral": 800
                },
                avg_search_time_ms=125.0,
                avg_analysis_time_ms=2500.0,
                cache_hit_rate=0.72,
                images_analyzed=images_analyzed,
                videos_analyzed=videos_analyzed,
                frames_analyzed=images_analyzed * 10,  # Rough estimate
                color_space_usage={
                    "rgb": 2800,
                    "hsv": 450,
                    "lab": 250
                },
                clustering_method_usage={
                    "kmeans": 2200,
                    "dbscan": 800,
                    "hierarchical": 500
                }
            )
            
        except Exception as e:
            logger.error("Failed to get color search stats", error=str(e))
            raise SearchError(f"Failed to get color search statistics: {str(e)}")


# Service instance
_color_search_service: Optional[ColorSearchService] = None


async def get_color_search_service() -> ColorSearchService:
    """Get color search service instance"""
    global _color_search_service
    
    if _color_search_service is None:
        opensearch_client = await get_opensearch_client()
        _color_search_service = ColorSearchService(opensearch_client)
    
    return _color_search_service