"""Property-based and unit tests for confidence scoring module.

Feature: aarogya-sahayak
This module tests the confidence scoring formula and guardrail rules
using property-based testing with Hypothesis to validate correctness
across a wide range of randomly generated inputs.
"""

import pytest
from hypothesis import given, settings, strategies as st
from src.backend.models import EvidenceHit
from src.backend.services.confidence_scoring import calculate_confidence


# Hypothesis strategies for generating test data
@st.composite
def evidence_hit_strategy(draw):
    """Generate a valid EvidenceHit with random cosine similarity."""
    similarity = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    return EvidenceHit(
        title=draw(st.text(min_size=5, max_size=100)),
        pmcid=f"PMC{draw(st.integers(min_value=1000000, max_value=9999999))}",
        doi=f"10.{draw(st.integers(min_value=1000, max_value=9999))}/example.{draw(st.integers(min_value=2020, max_value=2024))}",
        snippet=draw(st.text(min_size=10, max_size=200)),
        cosine_similarity=similarity
    )


@st.composite
def three_evidence_hits_strategy(draw):
    """Generate exactly 3 evidence hits as required by the system."""
    return [
        draw(evidence_hit_strategy()),
        draw(evidence_hit_strategy()),
        draw(evidence_hit_strategy())
    ]


@st.composite
def action_item_dict_strategy(draw):
    """Generate a valid action item dictionary."""
    category = draw(st.sampled_from([
        "medication", "treatment", "diagnostic", "lifestyle", "followup"
    ]))
    return {
        "id": f"{draw(st.uuids())}",
        "text": draw(st.text(min_size=10, max_size=200)),
        "category": category,
        "severity": draw(st.sampled_from(["low", "medium", "high", "critical"])),
    }


# Property 3: Confidence Formula Correctness
# Validates: Requirements 4.1
@settings(max_examples=100)
@given(
    action_item=action_item_dict_strategy(),
    evidence_hits=three_evidence_hits_strategy(),
    model_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_property_confidence_formula_correctness(action_item, evidence_hits, model_score):
    """
    Property 3: Confidence Formula Correctness
    
    For any action item with known evidence hits and model score, the confidence
    value must equal 0.6 * max(cosine_similarity of evidence hits) + 0.4 * normalized_model_score,
    clamped to the range [0, 1].
    
    Feature: aarogya-sahayak, Property 3: Confidence Formula Correctness
    Validates: Requirements 4.1
    """
    # Calculate expected confidence using the formula
    max_similarity = max(hit.cosine_similarity for hit in evidence_hits)
    expected_confidence = 0.6 * max_similarity + 0.4 * model_score
    
    # Clamp to [0, 1] range
    expected_confidence = min(max(expected_confidence, 0.0), 1.0)
    
    # Calculate actual confidence using the function
    actual_confidence = calculate_confidence(action_item, evidence_hits, model_score)
    
    # Verify the formula is applied correctly (with small floating point tolerance)
    assert abs(actual_confidence - expected_confidence) < 1e-9, (
        f"Confidence formula mismatch: expected {expected_confidence:.6f}, "
        f"got {actual_confidence:.6f} for max_sim={max_similarity:.6f}, "
        f"model_score={model_score:.6f}"
    )
    
    # Verify confidence is in valid range
    assert 0.0 <= actual_confidence <= 1.0, (
        f"Confidence {actual_confidence} is outside valid range [0, 1]"
    )


# Property 4: Low Confidence Review Flag
# Validates: Requirements 4.2
@settings(max_examples=100)
@given(
    action_item=action_item_dict_strategy(),
    evidence_hits=three_evidence_hits_strategy(),
    model_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_property_low_confidence_review_flag(action_item, evidence_hits, model_score):
    """
    Property 4: Low Confidence Review Flag
    
    For any action item where the calculated confidence score is below 0.6,
    the clinician_review_required flag must be set to true.
    
    Feature: aarogya-sahayak, Property 4: Low Confidence Review Flag
    Validates: Requirements 4.2
    """
    # Calculate confidence
    confidence = calculate_confidence(action_item, evidence_hits, model_score)
    
    # Get the review flag that was set by calculate_confidence
    review_required = action_item.get("clinician_review_required", False)
    
    # Calculate expected confidence to determine if it's below threshold
    max_similarity = max(hit.cosine_similarity for hit in evidence_hits)
    expected_confidence = 0.6 * max_similarity + 0.4 * model_score
    expected_confidence = min(max(expected_confidence, 0.0), 1.0)
    
    # If confidence is below 0.6, review must be required
    # Note: High-risk categories (medication, treatment) also require review
    # regardless of confidence, so we check both conditions
    if expected_confidence < 0.6:
        assert review_required is True, (
            f"Low confidence ({expected_confidence:.6f} < 0.6) must set "
            f"clinician_review_required=True, but got {review_required} "
            f"for category={action_item.get('category')}"
        )
    
    # Additional check: if category is medication or treatment, review is always required
    category = action_item.get("category", "").lower()
    if category in ["medication", "treatment"]:
        assert review_required is True, (
            f"High-risk category '{category}' must always set "
            f"clinician_review_required=True, but got {review_required}"
        )


# Property 5: High-Risk Category Review Flag
# Validates: Requirements 4.3
@settings(max_examples=100)
@given(
    high_risk_category=st.sampled_from(["medication", "treatment"]),
    evidence_hits=three_evidence_hits_strategy(),
    model_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_property_high_risk_category_review_flag(high_risk_category, evidence_hits, model_score):
    """
    Property 5: High-Risk Category Review Flag
    
    For any action item where the category is "medication" or "treatment",
    the clinician_review_required flag must be set to true, regardless of
    the confidence score.
    
    Feature: aarogya-sahayak, Property 5: High-Risk Category Review Flag
    Validates: Requirements 4.3
    """
    # Create action item with high-risk category
    action_item = {
        "id": "test-uuid",
        "text": f"Test {high_risk_category} recommendation",
        "category": high_risk_category,
        "severity": "medium"
    }
    
    # Calculate confidence (which will also set the review flag)
    confidence = calculate_confidence(action_item, evidence_hits, model_score)
    
    # Get the review flag that was set by calculate_confidence
    review_required = action_item.get("clinician_review_required", False)
    
    # Assert that review is ALWAYS required for high-risk categories
    # regardless of confidence score
    assert review_required is True, (
        f"High-risk category '{high_risk_category}' must ALWAYS set "
        f"clinician_review_required=True, but got {review_required} "
        f"(confidence={confidence:.6f}, model_score={model_score:.6f})"
    )
    
    # Additional verification: even with high confidence, review should be required
    max_similarity = max(hit.cosine_similarity for hit in evidence_hits)
    calculated_confidence = 0.6 * max_similarity + 0.4 * model_score
    
    # Even if confidence is >= 0.6, review must still be required for these categories
    if calculated_confidence >= 0.6:
        assert review_required is True, (
            f"High-risk category '{high_risk_category}' with high confidence "
            f"({calculated_confidence:.6f} >= 0.6) must STILL require review, "
            f"but clinician_review_required={review_required}"
        )
