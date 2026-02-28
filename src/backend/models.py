"""Core data models for Aarogya Sahayak system."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class EvidenceHit:
    """Evidence citation from medical literature with relevance score."""
    title: str
    pmcid: str
    doi: str
    snippet: str  # max 200 chars
    cosine_similarity: float  # 0-1 range


@dataclass
class ActionItem:
    """Structured clinical recommendation with confidence and evidence."""
    id: str  # UUID v4
    text: str
    category: str  # medication | treatment | diagnostic | lifestyle | followup
    severity: str  # low | medium | high | critical
    confidence: float  # 0-1, formula: 0.6*max_sim + 0.4*model_score
    clinician_review_required: bool
    evidence: List[EvidenceHit] = field(default_factory=list)  # exactly 3 items


@dataclass
class ClinicalNoteRequest:
    """Request payload for clinical note summarization."""
    clinical_note: str  # max 10000 chars
    language_preference: str = "ta"  # default Tamil
    request_id: Optional[str] = None  # UUID v4, optional


@dataclass
class SummaryResponse:
    """Complete response for clinical note summarization."""
    request_id: str  # UUID v4
    summary: str  # 3-8 sentences
    patient_summary: Dict[str, str]  # {"hi": "...", "ta": "..."}
    actions: List[ActionItem]
    sources: List[EvidenceHit]
    confidence: float  # 0-1, overall confidence
    hallucination_alert: bool
    processing_time_ms: int


@dataclass
class AuditLogEntry:
    """Tamper-evident audit log entry without PHI."""
    timestamp: str  # ISO 8601
    request_id: str  # UUID v4
    request_hash: str  # SHA-256
    response_hash: str  # SHA-256
    model_version: str  # e.g., "anthropic.claude-v2"
    latency_ms: int
    signed_by: str  # HMAC-SHA256 signature
    user_id: Optional[str] = None  # from JWT, hashed
    hallucination_alert: bool = False
