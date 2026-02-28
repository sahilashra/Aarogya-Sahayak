"""Unit tests for core data models."""

import pytest
from src.backend.models import (
    EvidenceHit,
    ActionItem,
    ClinicalNoteRequest,
    SummaryResponse,
    AuditLogEntry
)


def test_evidence_hit_creation():
    """Test EvidenceHit data class instantiation."""
    evidence = EvidenceHit(
        title="Test Article",
        pmcid="PMC1234567",
        doi="10.1234/test.2023",
        snippet="This is a test snippet from the article.",
        cosine_similarity=0.85
    )
    
    assert evidence.title == "Test Article"
    assert evidence.pmcid == "PMC1234567"
    assert evidence.doi == "10.1234/test.2023"
    assert evidence.cosine_similarity == 0.85
    assert 0.0 <= evidence.cosine_similarity <= 1.0


def test_action_item_creation(sample_evidence_hit):
    """Test ActionItem data class instantiation."""
    action = ActionItem(
        id="550e8400-e29b-41d4-a716-446655440000",
        text="Order HbA1c test",
        category="diagnostic",
        severity="medium",
        confidence=0.78,
        clinician_review_required=False,
        evidence=[sample_evidence_hit, sample_evidence_hit, sample_evidence_hit]
    )
    
    assert action.id == "550e8400-e29b-41d4-a716-446655440000"
    assert action.category == "diagnostic"
    assert action.severity == "medium"
    assert action.confidence == 0.78
    assert len(action.evidence) == 3
    assert action.clinician_review_required is False


def test_clinical_note_request_defaults():
    """Test ClinicalNoteRequest with default values."""
    request = ClinicalNoteRequest(
        clinical_note="Patient presents with symptoms..."
    )
    
    assert request.clinical_note == "Patient presents with symptoms..."
    assert request.language_preference == "ta"  # default Tamil
    assert request.request_id is None


def test_clinical_note_request_with_values():
    """Test ClinicalNoteRequest with explicit values."""
    request = ClinicalNoteRequest(
        clinical_note="Patient presents with symptoms...",
        language_preference="hi",
        request_id="123e4567-e89b-12d3-a456-426614174000"
    )
    
    assert request.language_preference == "hi"
    assert request.request_id == "123e4567-e89b-12d3-a456-426614174000"


def test_summary_response_structure(sample_action_item, sample_evidence_hit):
    """Test SummaryResponse data class structure."""
    response = SummaryResponse(
        request_id="123e4567-e89b-12d3-a456-426614174000",
        summary="Patient has elevated blood glucose. Recommend HbA1c test.",
        patient_summary={"hi": "Hindi summary", "ta": "Tamil summary"},
        actions=[sample_action_item],
        sources=[sample_evidence_hit, sample_evidence_hit, sample_evidence_hit],
        confidence=0.75,
        hallucination_alert=False,
        processing_time_ms=1500
    )
    
    assert response.request_id == "123e4567-e89b-12d3-a456-426614174000"
    assert len(response.actions) == 1
    assert len(response.sources) == 3
    assert "hi" in response.patient_summary
    assert "ta" in response.patient_summary
    assert response.confidence == 0.75
    assert response.hallucination_alert is False


def test_audit_log_entry_creation():
    """Test AuditLogEntry data class instantiation."""
    audit_entry = AuditLogEntry(
        timestamp="2024-01-15T10:30:00Z",
        request_id="123e4567-e89b-12d3-a456-426614174000",
        request_hash="abc123def456",
        response_hash="xyz789uvw012",
        model_version="anthropic.claude-v2",
        latency_ms=1500,
        signed_by="hmac_signature_here",
        user_id="hashed_user_id",
        hallucination_alert=False
    )
    
    assert audit_entry.timestamp == "2024-01-15T10:30:00Z"
    assert audit_entry.request_id == "123e4567-e89b-12d3-a456-426614174000"
    assert audit_entry.model_version == "anthropic.claude-v2"
    assert audit_entry.latency_ms == 1500
    assert audit_entry.hallucination_alert is False


def test_audit_log_entry_defaults():
    """Test AuditLogEntry with default values."""
    audit_entry = AuditLogEntry(
        timestamp="2024-01-15T10:30:00Z",
        request_id="123e4567-e89b-12d3-a456-426614174000",
        request_hash="abc123",
        response_hash="xyz789",
        model_version="anthropic.claude-v2",
        latency_ms=1500,
        signed_by="signature"
    )
    
    assert audit_entry.user_id is None
    assert audit_entry.hallucination_alert is False
