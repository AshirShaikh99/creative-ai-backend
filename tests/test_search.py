#!/usr/bin/env python
"""
Unit and integration tests for the search functionality.
"""

import os
import sys
import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict, Any
from dataclasses import asdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import search module
from app.utils.search import QdrantSearch, SearchResult
from app.service.qdrant_service import QdrantService
from qdrant_client.models import ScoredPoint, Filter, FieldCondition, Range, SearchParams


@pytest.fixture
def mock_qdrant_client():
    """Create a mock QdrantClient for testing."""
    mock_client = MagicMock()
    # Setup mock responses for common methods
    mock_client.get_collection.return_value = {"status": "green", "vectors_count": 100}
    return mock_client


@pytest.fixture
def mock_sentence_transformer():
    """Create a mock SentenceTransformer for testing."""
    with patch('app.utils.search.SentenceTransformer') as mock_transformer:
        # Configure the mock to return a fixed embedding
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_transformer.return_value = mock_model
        yield mock_transformer


@pytest.fixture
def mock_torch():
    """Create a mock torch module for testing."""
    with patch('app.utils.search.torch') as mock_torch:
        # Configure the mock to simulate CPU device
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__.return_value = None
        yield mock_torch


@pytest.fixture
def search_instance(mock_qdrant_client, mock_sentence_transformer, mock_torch):
    """Create a QdrantSearch instance with mocked dependencies."""
    search = QdrantSearch(qdrant_client=mock_qdrant_client)
    return search


@pytest.mark.unit
class TestQdrantSearchInit:
    """Test the initialization of QdrantSearch."""

    def test_init(self, search_instance, mock_qdrant_client):
        """Test that QdrantSearch initializes correctly."""
        assert search_instance.qdrant_client == mock_qdrant_client
        assert search_instance.device == 'cpu'
        assert search_instance.default_search_params is not None
        assert search_instance.payload_selector is not None


@pytest.mark.unit
class TestQdrantSearchMethods:
    """Test the individual methods of QdrantSearch."""

    def test_init_search_params(self, search_instance):
        """Test that search parameters are initialized correctly."""
        params = search_instance.default_search_params
        assert params.hnsw_ef == 256
        assert params.exact is True

    def test_init_payload_selector(self, search_instance):
        """Test that payload selector is initialized correctly."""
        selector = search_instance.payload_selector
        assert "created_at" in selector.exclude
        assert "updated_at" in selector.exclude
        assert "embedding" in selector.exclude

    def test_generate_cache_key(self, search_instance):
        """Test the cache key generation."""
        key1 = search_instance._generate_cache_key("query1", "collection1")
        key2 = search_instance._generate_cache_key("query1", "collection1")
        key3 = search_instance._generate_cache_key("query2", "collection1")
        
        # Same inputs should produce same key
        assert key1 == key2
        # Different inputs should produce different keys
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_get_embedding(self, search_instance):
        """Test the embedding generation."""
        # Patch the _get_embedding_cached method to return a fixed value
        with patch.object(search_instance, '_get_embedding_cached', return_value=(0.1, 0.2, 0.3)) as mock_cached:
            embedding = await search_instance._get_embedding("test query")
            assert embedding == [0.1, 0.2, 0.3]
            mock_cached.assert_called_once_with("test query")

    def test_build_filter_simple(self, search_instance):
        """Test building a simple filter."""
        conditions = {"field1": "value1", "field2": "value2"}
        filter_obj = search_instance._build_filter(conditions)
        
        assert isinstance(filter_obj, Filter)
        assert len(filter_obj.must) == 2
        
        # Check that the conditions were added correctly
        field_conditions = [cond for cond in filter_obj.must if isinstance(cond, FieldCondition)]
        assert len(field_conditions) == 2
        
        # Check field names and values
        field_names = [cond.key for cond in field_conditions]
        assert "field1" in field_names
        assert "field2" in field_names

    def test_build_filter_complex(self, search_instance):
        """Test building a complex filter with range and match conditions."""
        conditions = {
            "field1": {"match": "value1"},
            "field2": {"range": {"gt": 10, "lt": 20}}
        }
        filter_obj = search_instance._build_filter(conditions)
        
        assert isinstance(filter_obj, Filter)
        assert len(filter_obj.must) == 2
        
        # Check field names
        field_names = [cond.key for cond in filter_obj.must]
        assert "field1" in field_names
        assert "field2" in field_names
        
        # Find the range condition
        range_condition = next(cond for cond in filter_obj.must if cond.key == "field2")
        assert range_condition.range.gt == 10
        assert range_condition.range.lt == 20

    def test_process_results(self, search_instance):
        """Test processing of search results."""
        # Create mock search results
        mock_results = [
            MagicMock(
                payload={"content": "content1", "metadata": {"source": "doc1"}, "source": "file1"},
                score=0.95
            ),
            MagicMock(
                payload={"content": "content2", "metadata": {"source": "doc2"}, "source": "file2"},
                score=0.85
            )
        ]
        
        processed = search_instance._process_results(mock_results)
        
        assert len(processed) == 2
        assert all(isinstance(result, SearchResult) for result in processed)
        assert processed[0].content == "content1"
        assert processed[0].score == 0.95
        assert processed[0].source == "file1"
        assert processed[1].content == "content2"
        assert processed[1].score == 0.85
        assert processed[1].source == "file2"


@pytest.mark.asyncio
@pytest.mark.integration
class TestQdrantSearchIntegration:
    """Integration tests for the search method."""

    async def test_search_basic(self, search_instance, mock_qdrant_client):
        """Test basic search functionality."""
        # Setup mock for _get_embedding
        with patch.object(search_instance, '_get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]
            
            # Setup mock search results
            mock_result = MagicMock(
                payload={"content": "test content", "metadata": {"source": "test"}, "source": "test_file"},
                score=0.9
            )
            mock_qdrant_client.search.return_value = [mock_result]
            
            # Call search method
            results = await search_instance.search("test query", "test_collection")
            
            # Verify results
            assert len(results) == 1
            assert results[0].content == "test content"
            assert results[0].score == 0.9
            assert results[0].source == "test_file"
            
            # Verify method calls
            mock_get_embedding.assert_called_once_with("test query")
            mock_qdrant_client.search.assert_called_once()
            
            # Verify search parameters
            call_args = mock_qdrant_client.search.call_args[1]
            assert call_args["collection_name"] == "test_collection"
            assert call_args["query_vector"] == [0.1, 0.2, 0.3]
            assert call_args["limit"] == 5  # Default value
            assert call_args["score_threshold"] == 0.5  # Default value

    async def test_search_with_filter(self, search_instance, mock_qdrant_client):
        """Test search with filter conditions."""
        # Setup mock for _get_embedding
        with patch.object(search_instance, '_get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]
            
            # Setup mock search results
            mock_qdrant_client.search.return_value = []
            
            # Call search method with filter
            filter_conditions = {"field": "value"}
            await search_instance.search(
                "test query", 
                "test_collection", 
                filter_conditions=filter_conditions
            )
            
            # Verify filter was built and passed
            mock_qdrant_client.search.assert_called_once()
            call_args = mock_qdrant_client.search.call_args[1]
            assert "filter" in call_args
            assert isinstance(call_args["filter"], Filter)

    async def test_search_collection_not_found(self, search_instance, mock_qdrant_client):
        """Test search when collection doesn't exist."""
        # Setup mock for _get_embedding
        with patch.object(search_instance, '_get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]
            
            # Setup mock to raise exception for get_collection
            mock_qdrant_client.get_collection.side_effect = Exception("Collection not found")
            
            # Call search method
            results = await search_instance.search("test query", "nonexistent_collection")
            
            # Verify empty results returned
            assert len(results) == 0
            
            # Verify get_collection was called
            mock_qdrant_client.get_collection.assert_called_once_with("nonexistent_collection")
            
            # Verify search was not called
            mock_qdrant_client.search.assert_not_called()

    async def test_search_error_handling(self, search_instance, mock_qdrant_client):
        """Test error handling in search method."""
        # Setup mock for _get_embedding
        with patch.object(search_instance, '_get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1, 0.2, 0.3]
            
            # Setup mock to raise exception for search
            mock_qdrant_client.search.side_effect = Exception("Search error")
            
            # Call search method and expect exception
            with pytest.raises(Exception) as excinfo:
                await search_instance.search("test query", "test_collection")
            
            assert "Search error" in str(excinfo.value)


@pytest.mark.integration
class TestSearchResultClass:
    """Tests for the SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a SearchResult instance."""
        result = SearchResult(
            content="test content",
            metadata={"source": "test"},
            score=0.9,
            source="test_file"
        )
        
        assert result.content == "test content"
        assert result.metadata == {"source": "test"}
        assert result.score == 0.9
        assert result.source == "test_file"

    def test_search_result_serialization(self):
        """Test serializing a SearchResult to dict."""
        result = SearchResult(
            content="test content",
            metadata={"source": "test"},
            score=0.9,
            source="test_file"
        )
        
        result_dict = asdict(result)
        
        assert result_dict["content"] == "test content"
        assert result_dict["metadata"] == {"source": "test"}
        assert result_dict["score"] == 0.9
        assert result_dict["source"] == "test_file"