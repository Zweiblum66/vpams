"""
Tests for Fuzzy Search API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.schemas import FuzzyMatchType, FuzzinessType


@pytest.mark.asyncio
class TestFuzzySearchAPI:
    """Test fuzzy search API endpoints"""
    
    async def test_fuzzy_search_basic(self, client: AsyncClient):
        """Test basic fuzzy search"""
        data = {
            "query": "vidoe",  # Intentional typo
            "match_type": "adaptive",
            "fuzziness": "AUTO",
            "performance_mode": "moderate",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "vidoe",
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "total_hits": 5,
                "max_score": 1.5,
                "hits": [
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 1.5,
                        "source": {
                            "asset_id": "asset-1",
                            "name": "video_tutorial.mp4",
                            "description": "A video tutorial file"
                        },
                        "highlight": {
                            "name": ["<mark>video</mark>_tutorial.mp4"]
                        }
                    }
                ],
                "suggestions": None,
                "performance_info": None,
                "took": 25,
                "timed_out": False,
                "page": 1,
                "per_page": 10,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 1,
                    "avg_word_length": 5.0,
                    "contains_technical_terms": False,
                    "is_phrase": False
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "vidoe"
            assert result["match_type"] == "adaptive"
            assert result["fuzziness"] == "AUTO"
            assert result["total_hits"] == 5
            assert len(result["hits"]) == 1
            assert result["hits"][0]["source"]["name"] == "video_tutorial.mp4"
    
    async def test_fuzzy_search_with_suggestions(self, client: AsyncClient):
        """Test fuzzy search with suggestions enabled"""
        data = {
            "query": "documnet",
            "match_type": "single_term",
            "fuzziness": "1",
            "include_suggestions": True,
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "documnet",
                "match_type": "single_term",
                "fuzziness": "1",
                "total_hits": 3,
                "max_score": 1.2,
                "hits": [],
                "suggestions": [
                    {"text": "document", "score": 0.8, "freq": 100},
                    {"text": "documents", "score": 0.7, "freq": 80}
                ],
                "performance_info": None,
                "took": 30,
                "timed_out": False,
                "page": 1,
                "per_page": 5,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 1,
                    "avg_word_length": 8.0,
                    "contains_technical_terms": False,
                    "is_phrase": False
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "documnet"
            assert result["suggestions"] is not None
            assert len(result["suggestions"]) == 2
            assert result["suggestions"][0]["text"] == "document"
    
    async def test_fuzzy_search_with_performance_info(self, client: AsyncClient):
        """Test fuzzy search with performance information"""
        data = {
            "query": "test video file",
            "match_type": "multi_term",
            "fuzziness": "AUTO",
            "performance_mode": "strict",
            "include_performance_info": True,
            "size": 20
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "test video file",
                "match_type": "multi_term",
                "fuzziness": "AUTO",
                "total_hits": 15,
                "max_score": 2.1,
                "hits": [],
                "suggestions": None,
                "performance_info": {
                    "complexity_score": 75,
                    "estimated_time_ms": 150,
                    "performance_impact": "moderate",
                    "recommendations": [
                        "Consider using stricter fuzziness settings"
                    ]
                },
                "took": 45,
                "timed_out": False,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 3,
                    "avg_word_length": 4.7,
                    "contains_technical_terms": False,
                    "is_phrase": True
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["performance_info"] is not None
            assert result["performance_info"]["complexity_score"] == 75
            assert result["performance_info"]["performance_impact"] == "moderate"
            assert len(result["performance_info"]["recommendations"]) == 1
    
    async def test_fuzzy_search_phrase_mode(self, client: AsyncClient):
        """Test fuzzy search in phrase mode"""
        data = {
            "query": "test vidoe file",
            "match_type": "phrase",
            "fuzziness": "AUTO",
            "slop": 3,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "test vidoe file",
                "match_type": "phrase",
                "fuzziness": "AUTO",
                "total_hits": 8,
                "max_score": 1.8,
                "hits": [],
                "suggestions": None,
                "performance_info": None,
                "took": 35,
                "timed_out": False,
                "page": 1,
                "per_page": 10,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 3,
                    "avg_word_length": 4.0,
                    "contains_technical_terms": False,
                    "is_phrase": True
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["match_type"] == "phrase"
            assert result["query"] == "test vidoe file"
    
    async def test_fuzzy_search_cross_field_mode(self, client: AsyncClient):
        """Test fuzzy search in cross-field mode"""
        data = {
            "query": "documnet managment",
            "match_type": "cross_field",
            "fuzziness": "2",
            "fields": ["title", "description", "keywords"],
            "size": 15
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "documnet managment",
                "match_type": "cross_field",
                "fuzziness": "2",
                "total_hits": 12,
                "max_score": 1.6,
                "hits": [],
                "suggestions": None,
                "performance_info": None,
                "took": 40,
                "timed_out": False,
                "page": 1,
                "per_page": 15,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 2,
                    "avg_word_length": 9.0,
                    "contains_technical_terms": False,
                    "is_phrase": True
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["match_type"] == "cross_field"
            assert result["fuzziness"] == "2"
    
    async def test_fuzzy_search_validation_errors(self, client: AsyncClient):
        """Test fuzzy search validation errors"""
        # Test invalid match type
        data = {
            "query": "test",
            "match_type": "invalid_type",
            "fuzziness": "AUTO"
        }
        
        response = await client.post("/api/v1/search/fuzzy", json=data)
        assert response.status_code == 422
        
        # Test invalid fuzziness
        data = {
            "query": "test",
            "match_type": "adaptive",
            "fuzziness": "invalid_fuzziness"
        }
        
        response = await client.post("/api/v1/search/fuzzy", json=data)
        assert response.status_code == 422
        
        # Test invalid performance mode
        data = {
            "query": "test",
            "match_type": "adaptive",
            "fuzziness": "AUTO",
            "performance_mode": "invalid_mode"
        }
        
        response = await client.post("/api/v1/search/fuzzy", json=data)
        assert response.status_code == 422
        
        # Test empty query
        data = {
            "query": "",
            "match_type": "adaptive",
            "fuzziness": "AUTO"
        }
        
        response = await client.post("/api/v1/search/fuzzy", json=data)
        assert response.status_code == 422
    
    async def test_fuzzy_search_pagination(self, client: AsyncClient):
        """Test fuzzy search with pagination"""
        data = {
            "query": "test",
            "match_type": "adaptive",
            "fuzziness": "AUTO",
            "size": 5,
            "from": 10
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "test",
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "total_hits": 50,
                "max_score": 1.0,
                "hits": [],
                "suggestions": None,
                "performance_info": None,
                "took": 20,
                "timed_out": False,
                "page": 3,
                "per_page": 5,
                "total_pages": 10,
                "query_analysis": {}
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["page"] == 3
            assert result["per_page"] == 5
            assert result["total_pages"] == 10
    
    async def test_fuzzy_search_sorting(self, client: AsyncClient):
        """Test fuzzy search with sorting"""
        data = {
            "query": "test",
            "match_type": "adaptive",
            "fuzziness": "AUTO",
            "sort_by": "created_at",
            "sort_order": "asc"
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "test",
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "total_hits": 10,
                "max_score": 1.0,
                "hits": [],
                "suggestions": None,
                "performance_info": None,
                "took": 15,
                "timed_out": False,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "query_analysis": {}
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "test"
    
    async def test_fuzzy_search_performance_modes(self, client: AsyncClient):
        """Test fuzzy search with different performance modes"""
        performance_modes = ["strict", "moderate", "loose"]
        
        for mode in performance_modes:
            data = {
                "query": "test",
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "performance_mode": mode
            }
            
            with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
                mock_search.return_value = {
                    "query": "test",
                    "match_type": "adaptive",
                    "fuzziness": "AUTO",
                    "total_hits": 5,
                    "max_score": 1.0,
                    "hits": [],
                    "suggestions": None,
                    "performance_info": None,
                    "took": 20,
                    "timed_out": False,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 1,
                    "query_analysis": {}
                }
                
                response = await client.post("/api/v1/search/fuzzy", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["query"] == "test"
    
    async def test_fuzzy_search_advanced_parameters(self, client: AsyncClient):
        """Test fuzzy search with advanced parameters"""
        data = {
            "query": "test",
            "match_type": "single_term",
            "fuzziness": "AUTO",
            "prefix_length": 2,
            "max_expansions": 100,
            "transpositions": False,
            "slop": 5
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "test",
                "match_type": "single_term",
                "fuzziness": "AUTO",
                "total_hits": 3,
                "max_score": 1.0,
                "hits": [],
                "suggestions": None,
                "performance_info": None,
                "took": 25,
                "timed_out": False,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "query_analysis": {}
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["match_type"] == "single_term"


@pytest.mark.asyncio
class TestFuzzySuggestionsAPI:
    """Test fuzzy suggestions API endpoints"""
    
    async def test_fuzzy_suggestions_basic(self, client: AsyncClient):
        """Test basic fuzzy suggestions"""
        data = {
            "text": "vidoe",
            "field": "title",
            "size": 5,
            "fuzziness": "AUTO"
        }
        
        with patch('src.services.search_service.SearchService') as mock_service:
            mock_service.return_value.client.search.return_value = {
                "suggest": {
                    "fuzzy_suggest": [
                        {
                            "text": "vidoe",
                            "offset": 0,
                            "length": 5,
                            "options": [
                                {
                                    "text": "video",
                                    "score": 0.8,
                                    "freq": 100
                                },
                                {
                                    "text": "videos",
                                    "score": 0.7,
                                    "freq": 80
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "vidoe"
            assert len(result["suggestions"]) == 2
            assert result["suggestions"][0]["text"] == "video"
            assert result["suggestions"][0]["score"] == 0.8
            assert result["metadata"]["field"] == "title"
            assert result["metadata"]["fuzziness"] == "AUTO"
    
    async def test_fuzzy_suggestions_with_different_fields(self, client: AsyncClient):
        """Test fuzzy suggestions with different fields"""
        fields = ["title", "description", "tags", "_all"]
        
        for field in fields:
            data = {
                "text": "documnet",
                "field": field,
                "size": 3,
                "fuzziness": "1"
            }
            
            with patch('src.services.search_service.SearchService') as mock_service:
                mock_service.return_value.client.search.return_value = {
                    "suggest": {
                        "fuzzy_suggest": [
                            {
                                "text": "documnet",
                                "offset": 0,
                                "length": 8,
                                "options": [
                                    {
                                        "text": "document",
                                        "score": 0.9,
                                        "freq": 200
                                    }
                                ]
                            }
                        ]
                    }
                }
                
                response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["text"] == "documnet"
                assert result["metadata"]["field"] == field
    
    async def test_fuzzy_suggestions_with_fuzziness_levels(self, client: AsyncClient):
        """Test fuzzy suggestions with different fuzziness levels"""
        fuzziness_levels = ["AUTO", "1", "2", "3", "0.5"]
        
        for fuzziness in fuzziness_levels:
            data = {
                "text": "test",
                "field": "title",
                "size": 5,
                "fuzziness": fuzziness
            }
            
            with patch('src.services.search_service.SearchService') as mock_service:
                mock_service.return_value.client.search.return_value = {
                    "suggest": {
                        "fuzzy_suggest": [
                            {
                                "text": "test",
                                "offset": 0,
                                "length": 4,
                                "options": [
                                    {
                                        "text": "test",
                                        "score": 1.0,
                                        "freq": 100
                                    }
                                ]
                            }
                        ]
                    }
                }
                
                response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["metadata"]["fuzziness"] == fuzziness
    
    async def test_fuzzy_suggestions_no_results(self, client: AsyncClient):
        """Test fuzzy suggestions when no suggestions are found"""
        data = {
            "text": "xyz123abc",
            "field": "title",
            "size": 5,
            "fuzziness": "AUTO"
        }
        
        with patch('src.services.search_service.SearchService') as mock_service:
            mock_service.return_value.client.search.return_value = {
                "suggest": {
                    "fuzzy_suggest": [
                        {
                            "text": "xyz123abc",
                            "offset": 0,
                            "length": 9,
                            "options": []
                        }
                    ]
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "xyz123abc"
            assert len(result["suggestions"]) == 0
    
    async def test_fuzzy_suggestions_validation_errors(self, client: AsyncClient):
        """Test fuzzy suggestions validation errors"""
        # Test empty text
        data = {
            "text": "",
            "field": "title",
            "size": 5,
            "fuzziness": "AUTO"
        }
        
        response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid fuzziness
        data = {
            "text": "test",
            "field": "title",
            "size": 5,
            "fuzziness": "invalid"
        }
        
        response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid size
        data = {
            "text": "test",
            "field": "title",
            "size": 0,
            "fuzziness": "AUTO"
        }
        
        response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
        assert response.status_code == 422
    
    async def test_fuzzy_suggestions_size_limits(self, client: AsyncClient):
        """Test fuzzy suggestions with size limits"""
        data = {
            "text": "test",
            "field": "title",
            "size": 10,
            "fuzziness": "AUTO"
        }
        
        # Create more suggestions than requested
        suggestions = []
        for i in range(15):
            suggestions.append({
                "text": f"test{i}",
                "score": 1.0 - (i * 0.1),
                "freq": 100 - (i * 5)
            })
        
        with patch('src.services.search_service.SearchService') as mock_service:
            mock_service.return_value.client.search.return_value = {
                "suggest": {
                    "fuzzy_suggest": [
                        {
                            "text": "test",
                            "offset": 0,
                            "length": 4,
                            "options": suggestions
                        }
                    ]
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            # Should limit to requested size
            assert len(result["suggestions"]) == 10
            # Should be sorted by score (highest first)
            assert result["suggestions"][0]["score"] >= result["suggestions"][1]["score"]
    
    async def test_fuzzy_suggestions_metadata(self, client: AsyncClient):
        """Test fuzzy suggestions metadata"""
        data = {
            "text": "test",
            "field": "description",
            "size": 3,
            "fuzziness": "2"
        }
        
        with patch('src.services.search_service.SearchService') as mock_service:
            mock_service.return_value.client.search.return_value = {
                "suggest": {
                    "fuzzy_suggest": [
                        {
                            "text": "test",
                            "offset": 0,
                            "length": 4,
                            "options": [
                                {
                                    "text": "test",
                                    "score": 1.0,
                                    "freq": 100
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert "metadata" in result
            assert result["metadata"]["field"] == "description"
            assert result["metadata"]["fuzziness"] == "2"
            assert result["metadata"]["total_suggestions"] == 1
            assert "took" in result
            assert result["took"] >= 0


@pytest.mark.asyncio
class TestFuzzySearchIntegration:
    """Integration tests for fuzzy search functionality"""
    
    async def test_fuzzy_search_typo_correction_workflow(self, client: AsyncClient):
        """Test complete typo correction workflow"""
        # 1. Search with typo
        search_data = {
            "query": "vidoe tutorial",
            "match_type": "adaptive",
            "fuzziness": "AUTO",
            "include_suggestions": True
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "vidoe tutorial",
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "total_hits": 5,
                "max_score": 1.5,
                "hits": [
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 1.5,
                        "source": {
                            "name": "video_tutorial_basics.mp4",
                            "description": "Basic video tutorial"
                        },
                        "highlight": {
                            "name": ["<mark>video</mark>_<mark>tutorial</mark>_basics.mp4"]
                        }
                    }
                ],
                "suggestions": [
                    {"text": "video tutorial", "score": 0.9, "freq": 150}
                ],
                "performance_info": None,
                "took": 35,
                "timed_out": False,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "query_analysis": {
                    "word_count": 2,
                    "avg_word_length": 6.5,
                    "contains_technical_terms": False,
                    "is_phrase": True
                }
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=search_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["total_hits"] == 5
            assert len(result["hits"]) == 1
            assert result["suggestions"] is not None
            assert result["suggestions"][0]["text"] == "video tutorial"
            
            # Verify fuzzy matching worked
            assert "<mark>video</mark>" in result["hits"][0]["highlight"]["name"][0]
            assert "<mark>tutorial</mark>" in result["hits"][0]["highlight"]["name"][0]
    
    async def test_fuzzy_search_performance_optimization(self, client: AsyncClient):
        """Test performance optimization for different query types"""
        test_cases = [
            {
                "query": "cat",  # Short query - should use strict mode
                "expected_performance": "low"
            },
            {
                "query": "video editing software tutorial",  # Long query - should use moderate mode
                "expected_performance": "moderate"
            },
            {
                "query": "very long complex query with many terms and technical specifications",  # Very long - should use loose mode
                "expected_performance": "high"
            }
        ]
        
        for case in test_cases:
            search_data = {
                "query": case["query"],
                "match_type": "adaptive",
                "fuzziness": "AUTO",
                "include_performance_info": True
            }
            
            with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
                mock_search.return_value = {
                    "query": case["query"],
                    "match_type": "adaptive",
                    "fuzziness": "AUTO",
                    "total_hits": 10,
                    "max_score": 1.0,
                    "hits": [],
                    "suggestions": None,
                    "performance_info": {
                        "complexity_score": 50,
                        "estimated_time_ms": 100,
                        "performance_impact": case["expected_performance"],
                        "recommendations": []
                    },
                    "took": 25,
                    "timed_out": False,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 1,
                    "query_analysis": {}
                }
                
                response = await client.post("/api/v1/search/fuzzy", json=search_data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["performance_info"]["performance_impact"] == case["expected_performance"]
    
    async def test_fuzzy_search_field_specific_matching(self, client: AsyncClient):
        """Test field-specific fuzzy matching"""
        search_data = {
            "query": "documnet",
            "match_type": "cross_field",
            "fuzziness": "AUTO",
            "fields": ["title", "description", "tags"]
        }
        
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.return_value = {
                "query": "documnet",
                "match_type": "cross_field",
                "fuzziness": "AUTO",
                "total_hits": 8,
                "max_score": 2.0,
                "hits": [
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 2.0,
                        "source": {
                            "title": "Document Management System",
                            "description": "A comprehensive document management solution",
                            "tags": ["document", "management", "system"]
                        },
                        "highlight": {
                            "title": ["<mark>Document</mark> Management System"],
                            "description": ["A comprehensive <mark>document</mark> management solution"],
                            "tags": ["<mark>document</mark>", "management", "system"]
                        }
                    }
                ],
                "suggestions": None,
                "performance_info": None,
                "took": 30,
                "timed_out": False,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "query_analysis": {}
            }
            
            response = await client.post("/api/v1/search/fuzzy", json=search_data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["total_hits"] == 8
            assert result["match_type"] == "cross_field"
            
            # Verify highlighting works across multiple fields
            highlight = result["hits"][0]["highlight"]
            assert "title" in highlight
            assert "description" in highlight
            assert "tags" in highlight
    
    async def test_fuzzy_search_error_handling(self, client: AsyncClient):
        """Test error handling in fuzzy search"""
        search_data = {
            "query": "test",
            "match_type": "adaptive",
            "fuzziness": "AUTO"
        }
        
        # Test search service error
        with patch('src.services.search_service.SearchService.fuzzy_search') as mock_search:
            mock_search.side_effect = Exception("Search service error")
            
            response = await client.post("/api/v1/search/fuzzy", json=search_data)
            
            assert response.status_code == 500
            assert "fuzzy search error" in response.json()["detail"].lower()
        
        # Test suggestion service error
        suggestion_data = {
            "text": "test",
            "field": "title",
            "size": 5,
            "fuzziness": "AUTO"
        }
        
        with patch('src.services.search_service.SearchService') as mock_service:
            mock_service.return_value.client.search.side_effect = Exception("Suggestion error")
            
            response = await client.post("/api/v1/search/fuzzy/suggestions", json=suggestion_data)
            
            assert response.status_code == 500
            assert "fuzzy suggestions error" in response.json()["detail"].lower()