"""Confidence scoring and guardrail logic for clinical recommendations.

This module implements the confidence scoring formula and guardrail rules
for determining when clinical review is required for action items.
"""

from typing import List, Dict
from src.backend.models import EvidenceHit


def calculate_confidence(
    action_item: Dict,
    evidence_hits: List[EvidenceHit],
    model_score: float = 0.5
) -> float:
    """
    Calculate confidence score for a clinical action item using evidence grounding.
    
    The confidence score combines retrieval quality (how well the action is grounded
    in medical literature) with model confidence (how certain the LLM is about the
    recommendation). This dual-signal approach ensures both evidence-based and
    model-based quality assessment.
    
    Formula:
        confidence = 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
    
    Where:
        - max_retrieval_similarity: Maximum cosine similarity among the top-3 
          evidence hits for this action (range: 0-1). Higher values indicate 
          stronger grounding in medical literature.
        - normalized_model_score: Bedrock model confidence score normalized to 
          [0,1] range. Default is 0.5 if unavailable from the model.
    
    Guardrail Rules Applied:
        1. If calculated confidence < 0.6, sets clinician_review_required = True
        2. If action category is 'medication' or 'treatment', always sets 
           clinician_review_required = True (high-risk categories)
    
    Args:
        action_item: Dictionary containing action item data, must include 'category' key
        evidence_hits: List of exactly 3 EvidenceHit objects with cosine_similarity scores
        model_score: Normalized model confidence score in [0,1] range (default: 0.5)
    
    Returns:
        Confidence score clamped to [0, 1] range
    
    Side Effects:
        Modifies action_item dict in-place by setting 'clinician_review_required' flag
    
    Examples:
        >>> action = {"category": "lifestyle", "text": "Increase physical activity"}
        >>> evidence = [
        ...     EvidenceHit("Title", "PMC123", "10.1234", "snippet", 0.85),
        ...     EvidenceHit("Title", "PMC456", "10.5678", "snippet", 0.72),
        ...     EvidenceHit("Title", "PMC789", "10.9012", "snippet", 0.68)
        ... ]
        >>> conf = calculate_confidence(action, evidence, model_score=0.7)
        >>> print(f"{conf:.2f}")  # 0.6 * 0.85 + 0.4 * 0.7 = 0.79
        0.79
        >>> action["clinician_review_required"]
        False
        
        >>> med_action = {"category": "medication", "text": "Prescribe metformin"}
        >>> conf = calculate_confidence(med_action, evidence, model_score=0.9)
        >>> med_action["clinician_review_required"]  # Always True for medication
        True
    
    Requirements:
        - Implements Requirements 4.1 (confidence formula)
        - Implements Requirements 4.2 (low confidence review flag)
        - Implements Requirements 4.3 (high-risk category review flag)
        - Implements Requirements 4.4 (formula documentation)
        - Implements Requirements 4.5 (confidence range validation)
    """
    # Validate inputs
    if not evidence_hits:
        raise ValueError("evidence_hits cannot be empty")
    
    if len(evidence_hits) != 3:
        raise ValueError(f"Expected exactly 3 evidence hits, got {len(evidence_hits)}")
    
    if not 0.0 <= model_score <= 1.0:
        raise ValueError(f"model_score must be in [0,1] range, got {model_score}")
    
    # Extract maximum similarity from evidence hits
    max_retrieval_similarity = max(hit.cosine_similarity for hit in evidence_hits)
    
    # Apply confidence formula: 60% weight on retrieval, 40% weight on model
    confidence = 0.6 * max_retrieval_similarity + 0.4 * model_score
    
    # Clamp to [0, 1] range (should already be in range, but ensure it)
    confidence = min(max(confidence, 0.0), 1.0)
    
    # Apply guardrail rules
    category = action_item.get("category", "").lower()
    
    # Rule 1: Low confidence requires review
    if confidence < 0.6:
        action_item["clinician_review_required"] = True
    # Rule 2: High-risk categories always require review
    elif category in ["medication", "treatment"]:
        action_item["clinician_review_required"] = True
    else:
        action_item["clinician_review_required"] = False
    
    return confidence
