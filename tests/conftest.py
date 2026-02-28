"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_clinical_note():
    """Sample de-identified clinical note for testing."""
    return """
    Patient presents with elevated blood glucose levels (fasting: 180 mg/dL).
    History of type 2 diabetes mellitus for 5 years.
    Current medications: Metformin 500mg twice daily.
    Blood pressure: 140/90 mmHg.
    Recommend HbA1c test and dietary counseling.
    """


@pytest.fixture
def sample_evidence_hit():
    """Sample evidence hit for testing."""
    from src.backend.models import EvidenceHit
    return EvidenceHit(
        title="Management of Type 2 Diabetes",
        pmcid="PMC1234567",
        doi="10.1234/example.2023",
        snippet="Metformin is first-line therapy for type 2 diabetes...",
        cosine_similarity=0.85
    )


@pytest.fixture
def sample_action_item(sample_evidence_hit):
    """Sample action item for testing."""
    from src.backend.models import ActionItem
    return ActionItem(
        id="550e8400-e29b-41d4-a716-446655440000",
        text="Order HbA1c test to assess glycemic control",
        category="diagnostic",
        severity="medium",
        confidence=0.78,
        clinician_review_required=False,
        evidence=[sample_evidence_hit] * 3
    )
