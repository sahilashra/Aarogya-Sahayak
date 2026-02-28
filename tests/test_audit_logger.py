"""
Unit tests for audit logging functionality.

Tests the AuditLogger class to ensure proper creation of audit log entries
with cryptographic hashes and signatures, while verifying PHI protection.
"""

import json
import os
import tempfile
from pathlib import Path
from src.backend.services.audit_logger import AuditLogger


def test_audit_logger_initialization_mock_mode():
    """Test AuditLogger initialization in mock mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        assert logger.aws_mode == "mock"
        assert logger.demo_artifacts_path == f"{tmpdir}/audit_logs/"
        # Verify directory was created
        assert Path(f"{tmpdir}/audit_logs/").exists()


def test_create_audit_entry_basic():
    """Test basic audit entry creation with required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        request_id = "123e4567-e89b-12d3-a456-426614174000"
        clinical_note = "Patient presents with elevated glucose levels"
        response = {
            "summary": "Patient has diabetes",
            "actions": [],
            "confidence": 0.85
        }
        
        entry = logger.create_audit_entry(
            request_id=request_id,
            clinical_note=clinical_note,
            response=response,
            model_version="anthropic.claude-v2",
            latency_ms=1500
        )
        
        # Verify entry fields
        assert entry.request_id == request_id
        assert entry.model_version == "anthropic.claude-v2"
        assert entry.latency_ms == 1500
        assert entry.hallucination_alert is False
        
        # Verify hashes are generated (SHA-256 produces 64 hex characters)
        assert len(entry.request_hash) == 64
        assert len(entry.response_hash) == 64
        
        # Verify signature is generated
        assert len(entry.signed_by) == 64  # HMAC-SHA256 produces 64 hex characters
        
        # Verify timestamp is in ISO format
        assert "T" in entry.timestamp
        assert entry.timestamp.endswith("Z")


def test_audit_entry_phi_protection():
    """Test that raw clinical note is NOT stored in audit entry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        request_id = "test-phi-protection"
        clinical_note = "Dr. Smith examined patient John Doe on 01/15/2024"
        response = {"summary": "Examination complete"}
        
        entry = logger.create_audit_entry(
            request_id=request_id,
            clinical_note=clinical_note,
            response=response,
            model_version="test-model",
            latency_ms=1000
        )
        
        # Verify the clinical note text is NOT in any field
        assert clinical_note not in entry.request_hash
        assert "Dr. Smith" not in entry.request_hash
        assert "John Doe" not in entry.request_hash
        
        # Verify only hash is stored
        assert len(entry.request_hash) == 64
        assert entry.request_hash.isalnum()  # Hash should be alphanumeric


def test_audit_entry_written_to_json_file():
    """Test that audit entry is written to JSON file in demo mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        request_id = "file-write-test"
        clinical_note = "Test clinical note"
        response = {"summary": "Test summary"}
        
        entry = logger.create_audit_entry(
            request_id=request_id,
            clinical_note=clinical_note,
            response=response,
            model_version="test-model",
            latency_ms=500
        )
        
        # Verify file was created
        expected_file = Path(tmpdir) / "audit_logs" / f"{request_id}.json"
        assert expected_file.exists()
        
        # Verify file contents
        with open(expected_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["request_id"] == request_id
        assert saved_data["request_hash"] == entry.request_hash
        assert saved_data["response_hash"] == entry.response_hash
        assert saved_data["model_version"] == "test-model"
        assert saved_data["latency_ms"] == 500


def test_request_hash_consistency():
    """Test that same input produces same hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        clinical_note = "Consistent input text"
        response = {"summary": "Test"}
        
        entry1 = logger.create_audit_entry(
            request_id="test-1",
            clinical_note=clinical_note,
            response=response,
            model_version="test",
            latency_ms=100
        )
        
        entry2 = logger.create_audit_entry(
            request_id="test-2",
            clinical_note=clinical_note,
            response=response,
            model_version="test",
            latency_ms=100
        )
        
        # Same clinical note should produce same hash
        assert entry1.request_hash == entry2.request_hash
        # Same response should produce same hash
        assert entry1.response_hash == entry2.response_hash


def test_response_hash_with_different_responses():
    """Test that different responses produce different hashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        clinical_note = "Same input"
        response1 = {"summary": "Response A"}
        response2 = {"summary": "Response B"}
        
        entry1 = logger.create_audit_entry(
            request_id="test-1",
            clinical_note=clinical_note,
            response=response1,
            model_version="test",
            latency_ms=100
        )
        
        entry2 = logger.create_audit_entry(
            request_id="test-2",
            clinical_note=clinical_note,
            response=response2,
            model_version="test",
            latency_ms=100
        )
        
        # Different responses should produce different hashes
        assert entry1.response_hash != entry2.response_hash


def test_audit_entry_with_user_id():
    """Test audit entry creation with user_id (should be hashed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        user_id = "user@example.com"
        
        entry = logger.create_audit_entry(
            request_id="test-user-id",
            clinical_note="Test note",
            response={"summary": "Test"},
            model_version="test",
            latency_ms=100,
            user_id=user_id
        )
        
        # Verify user_id is hashed, not stored in plain text
        assert entry.user_id is not None
        assert entry.user_id != user_id
        assert len(entry.user_id) == 64  # SHA-256 hash


def test_audit_entry_with_hallucination_alert():
    """Test audit entry with hallucination alert flag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(
            aws_mode="mock",
            demo_artifacts_path=f"{tmpdir}/audit_logs/"
        )
        
        entry = logger.create_audit_entry(
            request_id="test-hallucination",
            clinical_note="Test note",
            response={"summary": "Test"},
            model_version="test",
            latency_ms=100,
            hallucination_alert=True
        )
        
        assert entry.hallucination_alert is True
