"""
Tests for sentiment analysis functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import torch
import numpy as np

from src.services.ml_service import MLService
from src.services.model_manager import ModelManager, ModelInfo
from src.core.exceptions import ValidationError, InferenceError


class TestSentimentAnalysis:
    """Test sentiment analysis functionality."""
    
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
        """Create mock model info for sentiment analysis."""
        mock_model = Mock()
        mock_tokenizer = Mock()
        
        # Mock tokenizer behavior
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        # Mock model output - positive sentiment
        mock_output = Mock()
        mock_output.logits = torch.tensor([[0.1, 0.2, 2.0]])  # negative, neutral, positive
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["negative", "neutral", "positive"]
            }
        )
        
        return model_info
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_positive(self, ml_service, model_manager, mock_model_info):
        """Test sentiment analysis with positive text."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_text = "I love this product! It's amazing and works perfectly."
        
        # Execute
        result = await ml_service.analyze_sentiment(test_text)
        
        # Verify
        assert result["sentiment"] == "positive"
        assert result["confidence"] in ["low", "medium", "high"]
        assert "compound_score" in result
        assert "max_score" in result
        assert "detailed_scores" in result
        assert result["model_name"] == "sentiment_analysis"
        assert result["text_length"] == len(test_text)
        assert len(result["detailed_scores"]) == 3  # negative, neutral, positive
        
        # Verify detailed scores structure
        for score in result["detailed_scores"]:
            assert "label" in score
            assert "score" in score
            assert score["label"] in ["negative", "neutral", "positive"]
            assert isinstance(score["score"], float)
            assert 0.0 <= score["score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_negative(self, ml_service, model_manager):
        """Test sentiment analysis with negative text."""
        # Setup mock model for negative sentiment
        mock_model = Mock()
        mock_tokenizer = Mock()
        
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        # Mock model output - negative sentiment
        mock_output = Mock()
        mock_output.logits = torch.tensor([[2.0, 0.2, 0.1]])  # negative, neutral, positive
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["negative", "neutral", "positive"]
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_text = "This is terrible! I hate it and it doesn't work at all."
        
        # Execute
        result = await ml_service.analyze_sentiment(test_text)
        
        # Verify
        assert result["sentiment"] == "negative"
        assert result["compound_score"] < 0  # Should be negative
        assert result["text_length"] == len(test_text)
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_neutral(self, ml_service, model_manager):
        """Test sentiment analysis with neutral text."""
        # Setup mock model for neutral sentiment
        mock_model = Mock()
        mock_tokenizer = Mock()
        
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        # Mock model output - neutral sentiment
        mock_output = Mock()
        mock_output.logits = torch.tensor([[0.1, 2.0, 0.2]])  # negative, neutral, positive
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["negative", "neutral", "positive"]
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data
        test_text = "This is a factual statement about the product specifications."
        
        # Execute
        result = await ml_service.analyze_sentiment(test_text)
        
        # Verify
        assert result["sentiment"] == "neutral"
        assert abs(result["compound_score"]) < 0.1  # Should be close to 0
        assert result["text_length"] == len(test_text)
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_validation_error(self, ml_service):
        """Test sentiment analysis with invalid input."""
        # Test empty text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.analyze_sentiment("")
        
        # Test None text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.analyze_sentiment(None)
        
        # Test non-string text
        with pytest.raises(ValidationError, match="Text input is required"):
            await ml_service.analyze_sentiment(123)
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_text_truncation(self, ml_service, model_manager, mock_model_info):
        """Test sentiment analysis with very long text."""
        # Setup
        model_manager.get_model = AsyncMock(return_value=mock_model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Test data - create text longer than 5000 characters
        test_text = "A" * 6000
        
        # Execute
        with patch.object(ml_service, '_run_sentiment_analysis') as mock_run:
            expected_result = {
                "sentiment": "positive",
                "confidence": "high",
                "compound_score": 0.8,
                "max_score": 0.9,
                "detailed_scores": [],
                "model_name": "sentiment_analysis",
                "text_length": 5000  # Should be truncated
            }
            mock_run.return_value = expected_result
            
            result = await ml_service.analyze_sentiment(test_text)
            
            # Verify text was truncated
            assert result["text_length"] == 5000
            # Check that the truncated text was passed to _run_sentiment_analysis
            mock_run.assert_called_once()
            passed_text = mock_run.call_args[0][0]
            assert len(passed_text) == 5000
    
    @pytest.mark.asyncio
    async def test_analyze_sentiment_cached_result(self, ml_service, model_manager):
        """Test sentiment analysis with cached result."""
        # Setup
        cached_result = {
            "sentiment": "positive",
            "confidence": "high",
            "compound_score": 0.8,
            "max_score": 0.9,
            "detailed_scores": [
                {"label": "negative", "score": 0.1},
                {"label": "neutral", "score": 0.1},
                {"label": "positive", "score": 0.8}
            ],
            "model_name": "sentiment_analysis",
            "text_length": 20
        }
        
        ml_service._get_cached_result = AsyncMock(return_value=cached_result)
        
        # Test data
        test_text = "This is a test message"
        
        # Execute
        result = await ml_service.analyze_sentiment(test_text)
        
        # Verify
        assert result == cached_result
        # Model should not be loaded when using cached result
        model_manager.get_model.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_sentiment_analysis_direct(self, ml_service, mock_model_info):
        """Test the _run_sentiment_analysis method directly."""
        # Setup
        test_text = "This is a test message"
        
        # Execute
        result = await ml_service._run_sentiment_analysis(test_text, mock_model_info)
        
        # Verify structure
        assert "sentiment" in result
        assert "confidence" in result
        assert "compound_score" in result
        assert "max_score" in result
        assert "detailed_scores" in result
        assert "model_name" in result
        assert "text_length" in result
        
        # Verify types
        assert isinstance(result["sentiment"], str)
        assert result["confidence"] in ["low", "medium", "high"]
        assert isinstance(result["compound_score"], float)
        assert isinstance(result["max_score"], float)
        assert isinstance(result["detailed_scores"], list)
        assert result["model_name"] == "sentiment_analysis"
        assert result["text_length"] == len(test_text)
    
    @pytest.mark.asyncio
    async def test_run_sentiment_analysis_missing_tokenizer(self, ml_service):
        """Test _run_sentiment_analysis with missing tokenizer."""
        # Setup model info without tokenizer
        mock_model = Mock()
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={"labels": ["negative", "neutral", "positive"]}
        )
        
        # Execute and verify error
        with pytest.raises(Exception, match="No tokenizer found"):
            await ml_service._run_sentiment_analysis("test", model_info)
    
    @pytest.mark.asyncio
    async def test_confidence_classification(self, ml_service, model_manager):
        """Test confidence classification logic."""
        # Test cases for different confidence levels
        test_cases = [
            (0.9, "high"),
            (0.8, "high"),
            (0.7, "medium"),
            (0.6, "medium"),
            (0.5, "low"),
            (0.4, "low")
        ]
        
        for max_score, expected_confidence in test_cases:
            # Create a mock model that returns the desired max score
            mock_model = Mock()
            mock_tokenizer = Mock()
            mock_tokenizer.return_value = {
                'input_ids': torch.tensor([[1, 2, 3, 4]]),
                'attention_mask': torch.tensor([[1, 1, 1, 1]])
            }
            
            # Create logits that will result in the desired max score after softmax
            # For softmax, we need one value much higher than others
            if max_score >= 0.9:
                logits = torch.tensor([[0.0, 0.0, 5.0]])  # High positive
            elif max_score >= 0.8:
                logits = torch.tensor([[0.0, 0.0, 3.0]])  # Medium-high positive
            elif max_score >= 0.6:
                logits = torch.tensor([[0.0, 0.0, 1.0]])  # Medium positive
            else:
                logits = torch.tensor([[0.0, 0.0, 0.5]])  # Low positive
            
            mock_output = Mock()
            mock_output.logits = logits
            mock_model.return_value = mock_output
            
            model_info = ModelInfo(
                name="sentiment_analysis",
                model_type="sentiment_analysis",
                model=mock_model,
                metadata={
                    "tokenizer": mock_tokenizer,
                    "labels": ["negative", "neutral", "positive"]
                }
            )
            
            result = await ml_service._run_sentiment_analysis("test", model_info)
            
            assert result["confidence"] == expected_confidence
    
    @pytest.mark.asyncio
    async def test_compound_score_calculation(self, ml_service, model_manager):
        """Test compound score calculation."""
        # Test positive compound score
        mock_model = Mock()
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        # Mock output with positive > negative
        mock_output = Mock()
        mock_output.logits = torch.tensor([[0.2, 0.1, 2.0]])  # neg: 0.2, neu: 0.1, pos: 2.0
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["negative", "neutral", "positive"]
            }
        )
        
        result = await ml_service._run_sentiment_analysis("test", model_info)
        
        # Should be positive compound score
        assert result["compound_score"] > 0
        
        # Test negative compound score
        mock_output.logits = torch.tensor([[2.0, 0.1, 0.2]])  # neg: 2.0, neu: 0.1, pos: 0.2
        mock_model.return_value = mock_output
        
        result = await ml_service._run_sentiment_analysis("test", model_info)
        
        # Should be negative compound score
        assert result["compound_score"] < 0
    
    @pytest.mark.asyncio
    async def test_custom_labels(self, ml_service, model_manager):
        """Test sentiment analysis with custom labels."""
        # Setup mock model with custom labels
        mock_model = Mock()
        mock_tokenizer = Mock()
        mock_tokenizer.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        
        mock_output = Mock()
        mock_output.logits = torch.tensor([[0.1, 2.0]])  # sad, happy
        mock_model.return_value = mock_output
        
        model_info = ModelInfo(
            name="sentiment_analysis",
            model_type="sentiment_analysis",
            model=mock_model,
            metadata={
                "tokenizer": mock_tokenizer,
                "labels": ["sad", "happy"]
            }
        )
        
        model_manager.get_model = AsyncMock(return_value=model_info)
        ml_service._get_cached_result = AsyncMock(return_value=None)
        ml_service._cache_result = AsyncMock()
        
        # Execute
        result = await ml_service.analyze_sentiment("test")
        
        # Verify custom labels are used
        assert result["sentiment"] == "happy"
        assert len(result["detailed_scores"]) == 2
        
        labels = [score["label"] for score in result["detailed_scores"]]
        assert "sad" in labels
        assert "happy" in labels