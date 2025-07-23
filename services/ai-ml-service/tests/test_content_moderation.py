"""
Tests for content moderation functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import torch
import numpy as np

from src.services.ml_service import MLService
from src.services.model_manager import ModelManager, ModelInfo
from src.core.exceptions import ValidationError, InferenceError


class TestContentModeration:
    """Test content moderation functionality."""
    
    @pytest.fixture
    def model_manager(self):
        """Create a mock model manager."""
        manager = Mock(spec=ModelManager)
        return manager
    
    @pytest.fixture
    def ml_service(self, model_manager):
        """Create ML service with mocked model manager."""
        service = MLService(model_manager)
        service.logger = Mock()
        service._processing_semaphore = AsyncMock()
        service._processing_semaphore.__aenter__ = AsyncMock(return_value=None)
        service._processing_semaphore.__aexit__ = AsyncMock(return_value=None)
        return service
    
    @pytest.fixture
    def mock_model_info(self):
        """Create mock model info for content moderation."""
        mock_model = Mock()
        mock_tokenizer = Mock()
        
        # Mock tokenizer behavior
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        # Mock model output
        mock_output = Mock()
        mock_output.logits = torch.tensor([[0.1, 0.9, 0.3, 0.7, 0.2, 0.8]])
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="content_moderation",
            model_type="content_moderation",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
            }
        )
        
        return model_info
    
    @pytest.mark.asyncio
    async def test_moderate_content_basic(self, ml_service, model_manager, mock_model_info):
        """Test basic content moderation functionality."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_text = "This is a test message"
        threshold = 0.5
        
        # Execute
        with patch.object(ml_service, '_run_content_moderation') as mock_run:
            expected_result = {
                "is_toxic": True,
                "severity": "high",
                "overall_score": 0.9,
                "flagged_categories": ["severe_toxic", "threat", "identity_hate"],
                "detailed_scores": [
                    {"category": "toxic", "score": 0.525, "flagged": True},
                    {"category": "severe_toxic", "score": 0.711, "flagged": True},
                    {"category": "obscene", "score": 0.574, "flagged": True},
                    {"category": "threat", "score": 0.669, "flagged": True},
                    {"category": "insult", "score": 0.550, "flagged": True},
                    {"category": "identity_hate", "score": 0.689, "flagged": True}
                ],
                "threshold": threshold,
                "model_name": "content_moderation",
                "text_length": len(test_text)
            }
            mock_run.return_value = expected_result
            
            result = await ml_service.moderate_content(test_text, threshold)
            
            # Verify
            assert result == expected_result
            mock_run.assert_called_once_with(test_text, mock_model_info, threshold)
    
    @pytest.mark.asyncio
    async def test_moderate_content_non_toxic(self, ml_service, model_manager, mock_model_info):
        """Test content moderation with non-toxic content."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_text = "This is a nice, friendly message"
        threshold = 0.5
        
        # Execute
        with patch.object(ml_service, '_run_content_moderation') as mock_run:
            expected_result = {
                "is_toxic": False,
                "severity": "low",
                "overall_score": 0.1,
                "flagged_categories": [],
                "detailed_scores": [
                    {"category": "toxic", "score": 0.1, "flagged": False},
                    {"category": "severe_toxic", "score": 0.05, "flagged": False},
                    {"category": "obscene", "score": 0.02, "flagged": False},
                    {"category": "threat", "score": 0.01, "flagged": False},
                    {"category": "insult", "score": 0.03, "flagged": False},
                    {"category": "identity_hate", "score": 0.02, "flagged": False}
                ],
                "threshold": threshold,
                "model_name": "content_moderation",
                "text_length": len(test_text)
            }
            mock_run.return_value = expected_result
            
            result = await ml_service.moderate_content(test_text, threshold)
            
            # Verify
            assert result == expected_result
            assert not result["is_toxic"]
            assert result["severity"] == "low"
    
    @pytest.mark.asyncio
    async def test_moderate_content_validation_error(self, ml_service):
        """Test content moderation with invalid input."""
        # Test empty text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.moderate_content("", 0.5)
        
        # Test None text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.moderate_content(None, 0.5)
        
        # Test non-string text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.moderate_content(123, 0.5)
    
    @pytest.mark.asyncio
    async def test_moderate_content_text_truncation(self, ml_service, model_manager, mock_model_info):
        """Test content moderation with very long text."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data - create text longer than 5000 characters
        test_text = "A" * 6000
        threshold = 0.5
        
        # Execute
        with patch.object(ml_service, '_run_content_moderation') as mock_run:
            expected_result = {
                "is_toxic": False,
                "severity": "low",
                "overall_score": 0.1,
                "flagged_categories": [],
                "detailed_scores": [],
                "threshold": threshold,
                "model_name": "content_moderation",
                "text_length": 5000  # Should be truncated
            }
            mock_run.return_value = expected_result
            
            result = await ml_service.moderate_content(test_text, threshold)
            
            # Verify text was truncated
            assert result["text_length"] == 5000
            # Check that the truncated text was passed to _run_content_moderation
            mock_run.assert_called_once()
            passed_text = mock_run.call_args[0][0]
            assert len(passed_text) == 5000
    
    @pytest.mark.asyncio
    async def test_moderate_content_cached_result(self, ml_service, model_manager):
        """Test content moderation with cached result."""
        # Setup
        cached_result = {
            "is_toxic": False,
            "severity": "low",
            "overall_score": 0.1,
            "flagged_categories": [],
            "detailed_scores": [],
            "threshold": 0.5,
            "model_name": "content_moderation",
            "text_length": 20
        }
        
        ml_service._get_cached_result = AsyncMock(return_value=cached_result)
        
        # Test data
        test_text = "This is a test message"
        threshold = 0.5
        
        # Execute
        result = await ml_service.moderate_content(test_text, threshold)
        
        # Verify
        assert result == cached_result
        # Model should not be loaded when using cached result
        model_manager.get_model.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_moderate_content_different_thresholds(self, ml_service, model_manager, mock_model_info):
        """Test content moderation with different thresholds."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        test_text = "This is a test message"
        
        # Test with high threshold (0.9)
        with patch.object(ml_service, '_run_content_moderation') as mock_run:
            expected_result_high = {
                "is_toxic": False,
                "severity": "medium",
                "overall_score": 0.7,
                "flagged_categories": [],
                "detailed_scores": [],
                "threshold": 0.9,
                "model_name": "content_moderation",
                "text_length": len(test_text)
            }
            mock_run.return_value = expected_result_high
            
            result = await ml_service.moderate_content(test_text, 0.9)
            assert result["threshold"] == 0.9
            assert not result["is_toxic"]  # Same scores but higher threshold
        
        # Test with low threshold (0.1)
        with patch.object(ml_service, '_run_content_moderation') as mock_run:
            expected_result_low = {
                "is_toxic": True,
                "severity": "medium",
                "overall_score": 0.7,
                "flagged_categories": ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"],
                "detailed_scores": [],
                "threshold": 0.1,
                "model_name": "content_moderation",
                "text_length": len(test_text)
            }
            mock_run.return_value = expected_result_low
            
            result = await ml_service.moderate_content(test_text, 0.1)
            assert result["threshold"] == 0.1
            assert result["is_toxic"]  # Same scores but lower threshold
    
    @pytest.mark.asyncio
    async def test_run_content_moderation_direct(self, ml_service, mock_model_info):
        """Test the _run_content_moderation method directly."""
        # Setup
        test_text = "This is a test message"
        threshold = 0.5
        
        # Execute
        result = await ml_service._run_content_moderation(test_text, mock_model_info, threshold)
        
        # Verify structure
        assert "is_toxic" in result
        assert "severity" in result
        assert "overall_score" in result
        assert "flagged_categories" in result
        assert "detailed_scores" in result
        assert "threshold" in result
        assert "model_name" in result
        assert "text_length" in result
        
        # Verify types
        assert isinstance(result["is_toxic"], bool)
        assert isinstance(result["severity"], str)
        assert isinstance(result["overall_score"], float)
        assert isinstance(result["flagged_categories"], list)
        assert isinstance(result["detailed_scores"], list)
        assert result["threshold"] == threshold
        assert result["model_name"] == "content_moderation"
        assert result["text_length"] == len(test_text)
    
    @pytest.mark.asyncio
    async def test_run_content_moderation_missing_tokenizer(self, ml_service):
        """Test _run_content_moderation with missing tokenizer."""
        # Setup model info without tokenizer
        mock_model = Mock()
        model_info = ModelInfo(
            name="content_moderation",
            model_type="content_moderation",
            model=mock_model,
            metadata={"labels": ["toxic", "severe_toxic"]}
        )
        
        # Execute and verify error
        with pytest.raises(Exception, match="No tokenizer found"):
            await ml_service._run_content_moderation("test", model_info, 0.5)
    
    @pytest.mark.asyncio
    async def test_severity_classification(self, ml_service, mock_model_info):
        """Test severity classification logic."""
        # Mock different score scenarios
        test_cases = [
            (0.9, "high"),
            (0.8, "high"),
            (0.7, "medium"),
            (0.5, "medium"),
            (0.3, "low"),
            (0.1, "low")
        ]
        
        for max_score, expected_severity in test_cases:
            # Create a mock model that returns the desired max score
            mock_model = Mock()
            mock_tokenizer = Mock()
            mock_tokenizer.return_value = {
                'input_ids': torch.tensor([[1, 2, 3, 4]]),
                'attention_mask': torch.tensor([[1, 1, 1, 1]])
            }
            
            # Create logits that will result in the desired max score after sigmoid
            # sigmoid(x) = max_score -> x = ln(max_score / (1 - max_score))
            if max_score >= 0.9999:
                max_score = 0.9999  # Avoid division by zero
            
            import math
            logit_value = math.log(max_score / (1 - max_score))
            
            mock_output = Mock()
            mock_output.logits = torch.tensor([[logit_value, -2.0, -2.0, -2.0, -2.0, -2.0]])
            mock_model.return_value = mock_output
            
            model_info = ModelInfo(
                name="content_moderation",
                model_type="content_moderation",
                model=mock_model,
                metadata={
                    "tokenizer": mock_tokenizer,
                    "labels": ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
                }
            )
            
            result = await ml_service._run_content_moderation("test", model_info, 0.5)
            
            assert result["severity"] == expected_severity
            assert abs(result["overall_score"] - max_score) < 0.01  # Allow for small numerical errors