"""
Amazon Q Orchestrator Module

This module orchestrates the full clinical note processing pipeline, coordinating
retrieval, summarization, confidence scoring, hallucination detection, translation,
and audit logging. It emulates Amazon Q workflow orchestration for sequencing
these operations in the correct order.
"""

import os
import uuid
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional
from datetime import datetime

from src.backend.models import (
    ActionItem,
    EvidenceHit,
    SummaryResponse,
    AuditLogEntry
)
from src.backend.lib.bedrock_client import BedrockClient
from src.backend.services.retrieval import RetrievalService
from src.backend.services.confidence_scoring import calculate_confidence
from src.backend.services.hallucination_detection import detect_hallucination


class QOrchestrator:
    """
    Orchestrator for the clinical note processing pipeline.
    
    This class coordinates the full workflow from clinical note input to
    final response with translations and audit logging. It implements the
    Amazon Q orchestration pattern, sequencing operations to ensure proper
    data flow and error handling.
    
    Pipeline Steps:
        1. Retrieval: Get top-3 evidence for note context
        2. Summarization: Generate summary + action items via Bedrock
        3. Evidence Matching: For each action, retrieve top-3 specific evidence
        4. Confidence Scoring: Calculate confidence for each action
        5. Hallucination Detection: Check overall grounding quality
        6. Translation: Generate Hindi and Tamil patient summaries
        7. Audit Log: Create signed audit entry
    """
    
    def __init__(
        self,
        bedrock_client: BedrockClient,
        retrieval_service: RetrievalService,
        aws_mode: str = "mock"
    ):
        """
        Initialize orchestrator with service dependencies.
        
        Args:
            bedrock_client: BedrockClient instance for LLM operations
            retrieval_service: RetrievalService instance for vector search
            aws_mode: "production" or "mock" for environment-specific behavior
        """
        self.bedrock_client = bedrock_client
        self.retrieval_service = retrieval_service
        self.aws_mode = aws_mode
    
    def process_clinical_note(
        self,
        clinical_note: str,
        request_id: Optional[str] = None,
        language_preference: str = "ta"
    ) -> Dict:
        """
        Orchestrate full pipeline: retrieval → summarization → guardrails → translation.
        
        This method implements the complete workflow for processing a clinical note,
        from initial evidence retrieval through final audit logging. Each step builds
        on the previous one, with error handling and validation at each stage.
        
        Args:
            clinical_note: Input clinical note text
            request_id: UUID for tracking (generated if not provided)
            language_preference: Target language for patient summary (default: "ta")
            
        Returns:
            Complete response dict matching API contract with keys:
            - request_id: UUID v4
            - summary: Clinical summary (3-8 sentences)
            - patient_summary: Dict with "hi" and "ta" translations
            - actions: List of ActionItem dicts with evidence
            - sources: List of top-3 overall evidence hits
            - confidence: Overall confidence score
            - hallucination_alert: Boolean flag
            - processing_time_ms: Processing duration
            
        Raises:
            Exception: If any pipeline step fails critically
            
        Requirements:
            Implements Requirements 7.4 (Amazon Q orchestration)
        """
        # Start timing
        start_time = time.time()
        
        # Generate request ID if not provided
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        try:
            # Step 1: Retrieve top-3 evidence for note context
            context_evidence = self._retrieve_context_evidence(clinical_note)
            
            # Step 2: Generate summary + action items via Bedrock
            summary_data = self._generate_summary(clinical_note, context_evidence)
            
            # Step 3: For each action, retrieve top-3 specific evidence
            actions_with_evidence = self._match_evidence_to_actions(
                summary_data["actions"],
                clinical_note
            )
            
            # Step 4: Calculate confidence for each action
            actions_with_confidence = self._calculate_action_confidence(
                actions_with_evidence,
                summary_data.get("model_score", 0.5)
            )
            
            # Step 5: Detect hallucinations
            hallucination_alert = self._detect_hallucinations(actions_with_confidence)
            
            # Step 6: Generate Hindi and Tamil translations
            patient_summary = self._generate_translations(summary_data["summary"])
            
            # Calculate overall confidence (average of action confidences)
            overall_confidence = self._calculate_overall_confidence(actions_with_confidence)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Build response
            response = {
                "request_id": request_id,
                "summary": summary_data["summary"],
                "patient_summary": patient_summary,
                "actions": [self._action_to_dict(action) for action in actions_with_confidence],
                "sources": [self._evidence_to_dict(ev) for ev in context_evidence],
                "confidence": overall_confidence,
                "hallucination_alert": hallucination_alert,
                "processing_time_ms": processing_time_ms
            }
            
            # Step 7: Create audit log entry
            audit_entry = self._create_audit_log(
                request_id=request_id,
                clinical_note=clinical_note,
                response=response,
                latency_ms=processing_time_ms,
                hallucination_alert=hallucination_alert
            )
            
            # Store audit entry (in production, write to DynamoDB)
            self._store_audit_log(audit_entry)
            
            return response
            
        except Exception as e:
            # Log error and re-raise
            print(f"Error in pipeline for request {request_id}: {e}")
            raise
    
    def _retrieve_context_evidence(self, clinical_note: str) -> List[EvidenceHit]:
        """
        Retrieve top-3 evidence hits for overall clinical note context.
        
        Args:
            clinical_note: Clinical note text
            
        Returns:
            List of 3 EvidenceHit objects
        """
        # Use the clinical note as the query for context retrieval
        evidence = self.retrieval_service.search(clinical_note, top_k=3)
        
        # Ensure we have exactly 3 results (pad with placeholders if needed)
        while len(evidence) < 3:
            evidence.append(EvidenceHit(
                title="No additional evidence available",
                pmcid="PMC0000000",
                doi="10.0000/unavailable",
                snippet="No additional evidence found for this query.",
                cosine_similarity=0.0
            ))
        
        return evidence[:3]
    
    def _generate_summary(
        self,
        clinical_note: str,
        context_evidence: List[EvidenceHit]
    ) -> Dict:
        """
        Generate clinical summary and action items using Bedrock.
        
        Args:
            clinical_note: Clinical note text
            context_evidence: Retrieved evidence for context
            
        Returns:
            Dict with keys: summary, actions, model_score
        """
        # Build context string from evidence
        context = "\n\n".join([
            f"Evidence {i+1}: {ev.title}\n{ev.snippet}"
            for i, ev in enumerate(context_evidence)
        ])
        
        # Call Bedrock for summarization
        summary_data = self.bedrock_client.summarize(clinical_note, context)
        
        return summary_data
    
    def _match_evidence_to_actions(
        self,
        actions: List[Dict],
        clinical_note: str
    ) -> List[ActionItem]:
        """
        Retrieve top-3 specific evidence for each action item.
        
        Args:
            actions: List of action dicts from Bedrock
            clinical_note: Original clinical note for context
            
        Returns:
            List of ActionItem objects with evidence attached
        """
        action_items = []
        
        # Extract key medical terms from clinical note for better matching
        note_lower = clinical_note.lower()
        medical_context = []
        if 'diabetes' in note_lower or 'glucose' in note_lower:
            medical_context.append('diabetes glucose management')
        if 'hypertension' in note_lower or 'blood pressure' in note_lower:
            medical_context.append('hypertension blood pressure')
        if 'respiratory' in note_lower or 'asthma' in note_lower or 'copd' in note_lower:
            medical_context.append('respiratory disease')
        if 'lipid' in note_lower or 'cholesterol' in note_lower:
            medical_context.append('lipid cholesterol')
        context_str = ' '.join(medical_context) if medical_context else clinical_note[:100]
        
        for action_dict in actions:
            # Generate unique ID for action
            action_id = str(uuid.uuid4())
            
            # Retrieve evidence specific to this action
            # Combine action text with medical context for better semantic matching
            action_query = f"{action_dict['text']} {context_str}"
            evidence = self.retrieval_service.search(action_query, top_k=3)
            
            # Ensure exactly 3 evidence hits
            while len(evidence) < 3:
                evidence.append(EvidenceHit(
                    title="No additional evidence available",
                    pmcid="PMC0000000",
                    doi="10.0000/unavailable",
                    snippet="No additional evidence found for this action.",
                    cosine_similarity=0.0
                ))
            
            # Create ActionItem object
            action_item = ActionItem(
                id=action_id,
                text=action_dict["text"],
                category=action_dict.get("category", "followup"),
                severity=action_dict.get("severity", "medium"),
                confidence=0.0,  # Will be calculated in next step
                clinician_review_required=False,  # Will be set by confidence scoring
                evidence=evidence[:3]
            )
            
            action_items.append(action_item)
        
        return action_items
    
    def _calculate_action_confidence(
        self,
        actions: List[ActionItem],
        model_score: float
    ) -> List[ActionItem]:
        """
        Calculate confidence scores for all actions and set review flags.
        
        Args:
            actions: List of ActionItem objects with evidence
            model_score: Normalized model confidence score
            
        Returns:
            List of ActionItem objects with confidence calculated
        """
        for action in actions:
            # Convert ActionItem to dict for calculate_confidence function
            action_dict = {
                "category": action.category,
                "text": action.text
            }
            
            # Calculate confidence (modifies action_dict in-place)
            confidence = calculate_confidence(
                action_dict,
                action.evidence,
                model_score
            )
            
            # Update ActionItem object
            action.confidence = confidence
            action.clinician_review_required = action_dict["clinician_review_required"]
        
        return actions
    
    def _detect_hallucinations(self, actions: List[ActionItem]) -> bool:
        """
        Detect potential hallucinations based on evidence grounding.
        
        Args:
            actions: List of ActionItem objects with evidence and confidence
            
        Returns:
            True if hallucination detected, False otherwise
        """
        return detect_hallucination(actions)
    
    def _generate_translations(self, summary: str) -> Dict[str, str]:
        """
        Generate Hindi and Tamil translations of patient summary.
        
        Args:
            summary: English clinical summary
            
        Returns:
            Dict with "hi" and "ta" keys containing translations
        """
        # Generate Hindi translation
        hindi_translation = self.bedrock_client.generate_translation(summary, "hi")
        
        # Generate Tamil translation
        tamil_translation = self.bedrock_client.generate_translation(summary, "ta")
        
        return {
            "hi": hindi_translation,
            "ta": tamil_translation
        }
    
    def _calculate_overall_confidence(self, actions: List[ActionItem]) -> float:
        """
        Calculate overall confidence as average of action confidences.
        
        Args:
            actions: List of ActionItem objects with confidence scores
            
        Returns:
            Average confidence score in [0, 1] range
        """
        if not actions:
            return 0.5  # Default confidence if no actions
        
        total_confidence = sum(action.confidence for action in actions)
        return total_confidence / len(actions)
    
    def _create_audit_log(
        self,
        request_id: str,
        clinical_note: str,
        response: Dict,
        latency_ms: int,
        hallucination_alert: bool
    ) -> AuditLogEntry:
        """
        Create audit log entry with hashes and signature.
        
        Args:
            request_id: Request UUID
            clinical_note: Original clinical note
            response: Response dict
            latency_ms: Processing time in milliseconds
            hallucination_alert: Hallucination detection flag
            
        Returns:
            AuditLogEntry object
        """
        # Generate timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Calculate request hash (SHA-256 of clinical note)
        request_hash = hashlib.sha256(clinical_note.encode()).hexdigest()
        
        # Calculate response hash (SHA-256 of response JSON)
        response_json = json.dumps(response, sort_keys=True)
        response_hash = hashlib.sha256(response_json.encode()).hexdigest()
        
        # Get model version
        model_version = "anthropic.claude-v2" if self.aws_mode == "production" else "mock-model-v1"
        
        # Generate HMAC signature
        signature = self._generate_hmac_signature(request_hash, response_hash)
        
        # Create audit log entry
        audit_entry = AuditLogEntry(
            timestamp=timestamp,
            request_id=request_id,
            request_hash=request_hash,
            response_hash=response_hash,
            model_version=model_version,
            latency_ms=latency_ms,
            signed_by=signature,
            hallucination_alert=hallucination_alert
        )
        
        return audit_entry
    
    def _generate_hmac_signature(self, request_hash: str, response_hash: str) -> str:
        import hmac as hmac_lib
        import hashlib
        import base64

        signing_key_b64 = os.environ.get("AUDIT_SIGNING_KEY")
        if signing_key_b64:
            signing_key = base64.b64decode(signing_key_b64)
        else:
            signing_key = b"demo-mock-signing-key-not-for-production"

        message = f"{request_hash}:{response_hash}".encode()
        return hmac_lib.new(signing_key, message, hashlib.sha256).hexdigest()

    
    def _store_audit_log(self, audit_entry: AuditLogEntry):
        """
        Store audit log entry to DynamoDB (production) or JSON file (demo).
        
        Args:
            audit_entry: AuditLogEntry object to store
        """
        if self.aws_mode == "production":
            # TODO: Write to DynamoDB
            # This would use boto3 to write to the audit logs table
            pass
        else:
            # Write to demo artifacts directory
            import os
            
            artifacts_dir = "demo/_artifacts/audit_logs"
            os.makedirs(artifacts_dir, exist_ok=True)
            
            # Write audit entry as JSON file
            filename = f"{audit_entry.request_id}.json"
            filepath = os.path.join(artifacts_dir, filename)
            
            # Convert audit entry to dict
            audit_dict = {
                "timestamp": audit_entry.timestamp,
                "request_id": audit_entry.request_id,
                "request_hash": audit_entry.request_hash,
                "response_hash": audit_entry.response_hash,
                "model_version": audit_entry.model_version,
                "latency_ms": audit_entry.latency_ms,
                "signed_by": audit_entry.signed_by,
                "hallucination_alert": audit_entry.hallucination_alert
            }
            
            with open(filepath, 'w') as f:
                json.dump(audit_dict, f, indent=2)
    
    def _action_to_dict(self, action: ActionItem) -> Dict:
        """Convert ActionItem to dict for JSON serialization."""
        return {
            "id": action.id,
            "text": action.text,
            "category": action.category,
            "severity": action.severity,
            "confidence": action.confidence,
            "clinician_review_required": action.clinician_review_required,
            "evidence": [self._evidence_to_dict(ev) for ev in action.evidence]
        }
    
    def _evidence_to_dict(self, evidence: EvidenceHit) -> Dict:
        """Convert EvidenceHit to dict for JSON serialization."""
        return {
            "title": evidence.title,
            "pmcid": evidence.pmcid,
            "doi": evidence.doi,
            "snippet": evidence.snippet,
            "cosine_similarity": evidence.cosine_similarity
        }
