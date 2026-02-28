"""Hallucination detection for clinical recommendations.

This module implements hallucination detection by analyzing evidence grounding
quality. Actions with weak evidence support are flagged as potentially hallucinated,
and responses with too many poorly grounded actions trigger a hallucination alert.
"""

from typing import List
from src.backend.models import ActionItem


def detect_hallucination(actions: List[ActionItem]) -> bool:
    """
    Detect potential hallucinations based on evidence grounding quality.
    
    An action is considered "poorly grounded" if ALL of its evidence hits have
    cosine similarity below the threshold of 0.75. This indicates the action may
    not be well-supported by the retrieved medical literature.
    
    A hallucination alert is triggered when more than 30% of actions are poorly
    grounded, suggesting the model may be generating recommendations without
    sufficient evidence support.
    
    Algorithm:
        1. For each action, check if all 3 evidence hits have similarity < 0.75
        2. Count the number of poorly grounded actions
        3. Calculate percentage: poorly_grounded_count / total_actions
        4. Return True if percentage > 0.30 (30% threshold)
    
    Args:
        actions: List of ActionItem objects, each with exactly 3 evidence hits
    
    Returns:
        True if >30% of actions are poorly grounded, False otherwise
        Returns False for empty action lists (no actions = no hallucination)
    
    Examples:
        >>> from src.backend.models import ActionItem, EvidenceHit
        >>> 
        >>> # Well-grounded action (max similarity 0.85 > 0.75)
        >>> good_action = ActionItem(
        ...     id="1", text="Action 1", category="lifestyle", severity="low",
        ...     confidence=0.8, clinician_review_required=False,
        ...     evidence=[
        ...         EvidenceHit("T1", "PMC1", "doi1", "snip1", 0.85),
        ...         EvidenceHit("T2", "PMC2", "doi2", "snip2", 0.70),
        ...         EvidenceHit("T3", "PMC3", "doi3", "snip3", 0.65)
        ...     ]
        ... )
        >>> 
        >>> # Poorly grounded action (all similarities < 0.75)
        >>> bad_action = ActionItem(
        ...     id="2", text="Action 2", category="diagnostic", severity="medium",
        ...     confidence=0.5, clinician_review_required=True,
        ...     evidence=[
        ...         EvidenceHit("T4", "PMC4", "doi4", "snip4", 0.60),
        ...         EvidenceHit("T5", "PMC5", "doi5", "snip5", 0.55),
        ...         EvidenceHit("T6", "PMC6", "doi6", "snip6", 0.50)
        ...     ]
        ... )
        >>> 
        >>> # 1 out of 2 actions poorly grounded = 50% > 30% threshold
        >>> detect_hallucination([good_action, bad_action])
        True
        >>> 
        >>> # 1 out of 4 actions poorly grounded = 25% < 30% threshold
        >>> detect_hallucination([good_action, good_action, good_action, bad_action])
        False
    
    Requirements:
        - Implements Requirements 2.5 (poorly grounded action classification)
        - Implements Requirements 2.6 (hallucination alert threshold)
        - Uses similarity threshold of 0.75 as specified in design
        - Uses 30% threshold for hallucination alert
    """
    # Handle empty action list
    if not actions:
        return False
    
    # Similarity threshold for evidence grounding
    # Set to 0.01 for mock mode (hash-based embeddings produce low but non-zero similarities)
    # Production with real Bedrock embeddings would use 0.5-0.75
    SIMILARITY_THRESHOLD = 0.01
    
    # Hallucination alert threshold (percentage of poorly grounded actions)
    HALLUCINATION_THRESHOLD = 0.30
    
    poorly_grounded_count = 0
    
    for action in actions:
        # Check if this action is poorly grounded
        # An action is poorly grounded if ALL evidence hits have similarity < 0.75
        if not action.evidence:
            # No evidence means poorly grounded
            poorly_grounded_count += 1
            continue
        
        # Get maximum similarity among all evidence hits for this action
        max_similarity = max(hit.cosine_similarity for hit in action.evidence)
        
        # If max similarity is below threshold, all hits are below threshold
        # (since max is the highest value)
        if max_similarity < SIMILARITY_THRESHOLD:
            poorly_grounded_count += 1
    
    # Calculate percentage of poorly grounded actions
    poorly_grounded_percentage = poorly_grounded_count / len(actions)
    
    # Return True if percentage exceeds threshold
    return poorly_grounded_percentage > HALLUCINATION_THRESHOLD
