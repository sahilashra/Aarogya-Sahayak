"""Unit tests for RetrievalService."""

import pytest
import tempfile
import os
from src.backend.services.retrieval import RetrievalService
from src.backend.lib.bedrock_client import BedrockClient
from src.backend.models import EvidenceHit


@pytest.fixture
def bedrock_client():
    """Create mock Bedrock client for testing."""
    return BedrockClient(aws_mode="mock", region="us-east-1")


@pytest.fixture
def temp_index_path():
    """Create temporary directory for index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def retrieval_service(temp_index_path, bedrock_client):
    """Create RetrievalService instance with empty index."""
    return RetrievalService(index_path=temp_index_path, bedrock_client=bedrock_client)


@pytest.fixture
def retrieval_service_with_data(temp_index_path, bedrock_client):
    """Create RetrievalService with sample documents."""
    service = RetrievalService(index_path=temp_index_path, bedrock_client=bedrock_client)
    
    # Add sample documents
    documents = [
        {
            "title": "Management of Type 2 Diabetes",
            "pmcid": "PMC1234567",
            "doi": "10.1234/diabetes.2023",
            "content": "Metformin is first-line therapy for type 2 diabetes mellitus. It reduces hepatic glucose production.",
            "snippet": "Metformin is first-line therapy for type 2 diabetes mellitus."
        },
        {
            "title": "Hypertension Treatment Guidelines",
            "pmcid": "PMC2345678",
            "doi": "10.1234/hypertension.2023",
            "content": "ACE inhibitors are recommended for hypertension management in diabetic patients.",
            "snippet": "ACE inhibitors are recommended for hypertension management."
        },
        {
            "title": "Cardiovascular Risk Assessment",
            "pmcid": "PMC3456789",
            "doi": "10.1234/cardio.2023",
            "content": "Regular monitoring of blood pressure and lipid levels is essential for cardiovascular risk assessment.",
            "snippet": "Regular monitoring of blood pressure and lipid levels is essential."
        }
    ]
    
    # Generate embeddings for documents
    embeddings = [bedrock_client.get_embeddings(doc["content"]) for doc in documents]
    
    # Add to index
    service.add_documents(documents, embeddings)
    
    return service


def test_retrieval_service_initialization(retrieval_service):
    """Test RetrievalService initializes correctly."""
    assert retrieval_service.index is not None
    assert retrieval_service.bedrock_client is not None
    assert isinstance(retrieval_service.embedding_cache, dict)


def test_search_empty_index(retrieval_service):
    """Test search on empty index returns empty results."""
    results = retrieval_service.search("diabetes management")
    assert results == []


def test_search_returns_top3(retrieval_service_with_data):
    """Test search returns exactly 3 results."""
    results = retrieval_service_with_data.search("diabetes treatment", top_k=3)
    assert len(results) == 3


def test_search_returns_evidence_hits(retrieval_service_with_data):
    """Test search returns EvidenceHit objects."""
    results = retrieval_service_with_data.search("diabetes", top_k=3)
    
    for result in results:
        # Check that result has all required attributes
        assert hasattr(result, 'title')
        assert hasattr(result, 'pmcid')
        assert hasattr(result, 'doi')
        assert hasattr(result, 'snippet')
        assert hasattr(result, 'cosine_similarity')
        # Verify it's an EvidenceHit by checking type name
        assert type(result).__name__ == 'EvidenceHit'


def test_cosine_similarity_range(retrieval_service_with_data):
    """Test all similarity scores are in [0, 1] range."""
    results = retrieval_service_with_data.search("medical treatment", top_k=3)
    
    for result in results:
        assert 0.0 <= result.cosine_similarity <= 1.0


def test_results_sorted_by_similarity(retrieval_service_with_data):
    """Test results are sorted by cosine_similarity descending."""
    results = retrieval_service_with_data.search("diabetes hypertension", top_k=3)
    
    similarities = [r.cosine_similarity for r in results]
    assert similarities == sorted(similarities, reverse=True)


def test_embedding_caching(retrieval_service_with_data):
    """Test that embeddings are cached for repeated queries."""
    query = "diabetes management"
    
    # First search
    results1 = retrieval_service_with_data.search(query, top_k=3)
    assert query in retrieval_service_with_data.embedding_cache
    
    # Second search should use cached embedding
    cached_embedding = retrieval_service_with_data.embedding_cache[query]
    results2 = retrieval_service_with_data.search(query, top_k=3)
    
    # Results should be identical
    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1.pmcid == r2.pmcid
        assert r1.cosine_similarity == r2.cosine_similarity


def test_add_documents(retrieval_service, bedrock_client):
    """Test adding documents to index."""
    documents = [
        {
            "title": "Test Article",
            "pmcid": "PMC9999999",
            "doi": "10.9999/test.2024",
            "content": "Test content for medical article.",
            "snippet": "Test content for medical article."
        }
    ]
    
    embeddings = [bedrock_client.get_embeddings(doc["content"]) for doc in documents]
    retrieval_service.add_documents(documents, embeddings)
    
    # Verify document was added
    assert retrieval_service.index.ntotal == 1
    assert len(retrieval_service.documents) == 1


def test_save_and_load_index(temp_index_path, bedrock_client):
    """Test saving and loading index from disk."""
    # Create service and add documents
    service1 = RetrievalService(index_path=temp_index_path, bedrock_client=bedrock_client)
    
    documents = [
        {
            "title": "Test Article",
            "pmcid": "PMC9999999",
            "doi": "10.9999/test.2024",
            "content": "Test content.",
            "snippet": "Test content."
        }
    ]
    
    embeddings = [bedrock_client.get_embeddings(doc["content"]) for doc in documents]
    service1.add_documents(documents, embeddings)
    service1.save_index()
    
    # Create new service and load index
    service2 = RetrievalService(index_path=temp_index_path, bedrock_client=bedrock_client)
    
    # Verify index was loaded
    assert service2.index.ntotal == 1
    assert len(service2.documents) == 1
    assert service2.documents[0]["pmcid"] == "PMC9999999"


def test_search_with_top_k_parameter(retrieval_service_with_data):
    """Test search respects top_k parameter."""
    results_1 = retrieval_service_with_data.search("medical", top_k=1)
    assert len(results_1) == 1
    
    results_2 = retrieval_service_with_data.search("medical", top_k=2)
    assert len(results_2) == 2
    
    results_3 = retrieval_service_with_data.search("medical", top_k=3)
    assert len(results_3) == 3
