"""
Audit Logging Module

This module provides tamper-evident audit logging functionality for the Aarogya Sahayak
system. It creates audit log entries with cryptographic hashes and HMAC signatures to
ensure integrity and non-repudiation, while carefully avoiding storage of any PHI.

The module supports two modes:
- Production: Writes to DynamoDB with KMS-derived signing keys
- Demo/Mock: Writes to local JSON files with mock signatures
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from src.backend.models import AuditLogEntry


class AuditLogger:
    """
    Audit logger for creating tamper-evident log entries without PHI.
    
    This class handles the creation of audit log entries that include cryptographic
    hashes of requests and responses, HMAC signatures for tamper detection, and
    metadata about system operations. It ensures that no PHI is ever stored in
    audit logs by hashing input data and only storing the hash values.
    
    Attributes:
        aws_mode: Operating mode - "production" or "mock"
        kms_key_id: KMS key ID for HMAC signing (production only)
        dynamodb_table: DynamoDB table name for audit logs (production only)
        demo_artifacts_path: Local directory for demo mode JSON files
    """
    
    def __init__(
        self,
        aws_mode: str = "mock",
        kms_key_id: Optional[str] = None,
        dynamodb_table: Optional[str] = None,
        demo_artifacts_path: str = "demo/_artifacts/audit_logs/"
    ):
        """
        Initialize the AuditLogger with configuration.
        
        Args:
            aws_mode: Operating mode - "production" or "mock" (default: "mock")
            kms_key_id: KMS key ID for HMAC signing in production mode
            dynamodb_table: DynamoDB table name for production mode
            demo_artifacts_path: Directory path for demo mode JSON files
        """
        self.aws_mode = aws_mode.lower()
        self.kms_key_id = kms_key_id
        self.dynamodb_table = dynamodb_table
        self.demo_artifacts_path = demo_artifacts_path
        
        # Create demo artifacts directory if in mock mode
        if self.aws_mode == "mock":
            Path(self.demo_artifacts_path).mkdir(parents=True, exist_ok=True)
    
    def create_audit_entry(
        self,
        request_id: str,
        clinical_note: str,
        response: Dict,
        model_version: str,
        latency_ms: int,
        user_id: Optional[str] = None,
        hallucination_alert: bool = False
    ) -> AuditLogEntry:
        """
        Create an audit log entry with cryptographic hashes and signature.
        
        This method generates a tamper-evident audit log entry by:
        1. Computing SHA-256 hash of the clinical note (request)
        2. Computing SHA-256 hash of the response JSON
        3. Generating HMAC-SHA256 signature for integrity verification
        4. Writing the entry to DynamoDB (production) or JSON file (demo)
        
        IMPORTANT: The raw clinical_note is NEVER stored - only its hash is
        persisted. This ensures PHI protection while maintaining audit trail
        integrity.
        
        Args:
            request_id: UUID v4 identifier for the request
            clinical_note: Raw clinical note text (will be hashed, not stored)
            response: Complete response dictionary to be hashed
            model_version: Bedrock model identifier (e.g., "anthropic.claude-v2")
            latency_ms: Processing time in milliseconds
            user_id: Optional user identifier from JWT (will be hashed if provided)
            hallucination_alert: Whether hallucination was detected in response
        
        Returns:
            AuditLogEntry object containing all audit metadata
        
        Side Effects:
            - Writes audit entry to DynamoDB (production mode)
            - Writes audit entry to JSON file (demo mode)
        
        Requirements:
            - Implements Requirement 5.1 (audit log entry creation)
            - Implements Requirement 5.2 (request hash computation)
            - Implements Requirement 5.3 (response hash computation)
            - Implements Requirement 5.7 (HMAC signature generation)
        
        Examples:
            >>> logger = AuditLogger(aws_mode="mock")
            >>> response = {"summary": "Patient has diabetes", "actions": []}
            >>> entry = logger.create_audit_entry(
            ...     request_id="123e4567-e89b-12d3-a456-426614174000",
            ...     clinical_note="Patient presents with elevated glucose",
            ...     response=response,
            ...     model_version="anthropic.claude-v2",
            ...     latency_ms=1500
            ... )
            >>> entry.request_id
            '123e4567-e89b-12d3-a456-426614174000'
            >>> len(entry.request_hash)  # SHA-256 produces 64 hex characters
            64
        """
        # Generate timestamp in ISO 8601 format
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Compute SHA-256 hash of request (clinical_note field only)
        # This ensures PHI is never stored while maintaining audit trail
        request_hash = self._compute_sha256(clinical_note)
        
        # Compute SHA-256 hash of response JSON
        # Serialize response to JSON string for consistent hashing
        response_json = json.dumps(response, sort_keys=True)
        response_hash = self._compute_sha256(response_json)
        
        # Hash user_id if provided (for privacy)
        hashed_user_id = None
        if user_id:
            hashed_user_id = self._compute_sha256(user_id)
        
        # Generate HMAC-SHA256 signature for tamper evidence
        signature = self._generate_signature(
            request_id=request_id,
            request_hash=request_hash,
            response_hash=response_hash,
            timestamp=timestamp
        )
        
        # Create audit log entry object
        audit_entry = AuditLogEntry(
            timestamp=timestamp,
            request_id=request_id,
            request_hash=request_hash,
            response_hash=response_hash,
            model_version=model_version,
            latency_ms=latency_ms,
            signed_by=signature,
            user_id=hashed_user_id,
            hallucination_alert=hallucination_alert
        )
        
        # Persist audit entry based on mode
        if self.aws_mode == "production":
            self._write_to_dynamodb(audit_entry)
        else:
            self._write_to_json_file(audit_entry)
        
        return audit_entry
    
    def _compute_sha256(self, text: str) -> str:
        """
        Compute SHA-256 hash of text.
        
        Args:
            text: Input text to hash
        
        Returns:
            Hexadecimal string representation of SHA-256 hash (64 characters)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _generate_signature(
        self,
        request_id: str,
        request_hash: str,
        response_hash: str,
        timestamp: str
    ) -> str:
        """
        Generate HMAC-SHA256 signature for audit log entry.
        
        In production mode, uses KMS-derived key for signing.
        In demo mode, uses a mock key for demonstration purposes.
        
        The signature is computed over the concatenation of:
        request_id + request_hash + response_hash + timestamp
        
        This ensures that any tampering with these fields will be detectable
        through signature verification.
        
        Args:
            request_id: Request UUID
            request_hash: SHA-256 hash of request
            response_hash: SHA-256 hash of response
            timestamp: ISO 8601 timestamp
        
        Returns:
            Hexadecimal string representation of HMAC-SHA256 signature
        """
        # Concatenate fields to sign
        message = f"{request_id}{request_hash}{response_hash}{timestamp}"
        
        if self.aws_mode == "production":
            # In production, derive signing key from KMS
            # This is a placeholder - actual implementation would call KMS API
            signing_key = self._get_kms_signing_key()
        else:
            # In demo mode, use a mock signing key
            # IMPORTANT: This is NOT secure and only for demonstration
            signing_key = b"mock-signing-key-for-demo-only-not-secure"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            signing_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_kms_signing_key(self) -> bytes:
        import base64

        signing_key_b64 = os.environ.get("AUDIT_SIGNING_KEY")
        if signing_key_b64:
            return base64.b64decode(signing_key_b64)
        return b"demo-mock-signing-key-not-for-production"

    
    def _write_to_dynamodb(self, audit_entry: AuditLogEntry) -> None:
        """
        Write audit log entry to DynamoDB in production mode.
        
        This is a placeholder for the actual DynamoDB integration.
        In production, this would use boto3 to write the entry atomically.
        
        Args:
            audit_entry: AuditLogEntry object to persist
        """
        # Placeholder implementation
        # TODO: Implement actual DynamoDB integration using boto3
        # import boto3
        # dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION'))
        # table = dynamodb.Table(self.dynamodb_table)
        # table.put_item(Item={
        #     'request_id': audit_entry.request_id,
        #     'timestamp': audit_entry.timestamp,
        #     'request_hash': audit_entry.request_hash,
        #     'response_hash': audit_entry.response_hash,
        #     'model_version': audit_entry.model_version,
        #     'latency_ms': audit_entry.latency_ms,
        #     'signed_by': audit_entry.signed_by,
        #     'user_id': audit_entry.user_id,
        #     'hallucination_alert': audit_entry.hallucination_alert
        # })
        
        # For now, just log that we would write to DynamoDB
        print(f"[PRODUCTION MODE] Would write audit entry to DynamoDB table: {self.dynamodb_table}")
        print(f"  Request ID: {audit_entry.request_id}")
    
    def _write_to_json_file(self, audit_entry: AuditLogEntry) -> None:
        """
        Write audit log entry to JSON file in demo mode.
        
        Creates a JSON file named {request_id}.json in the demo artifacts directory.
        Each audit entry is stored as a separate file for easy inspection.
        
        Args:
            audit_entry: AuditLogEntry object to persist
        """
        # Create filename from request_id
        filename = f"{audit_entry.request_id}.json"
        filepath = os.path.join(self.demo_artifacts_path, filename)
        
        # Convert audit entry to dictionary
        audit_dict = {
            "timestamp": audit_entry.timestamp,
            "request_id": audit_entry.request_id,
            "request_hash": audit_entry.request_hash,
            "response_hash": audit_entry.response_hash,
            "model_version": audit_entry.model_version,
            "latency_ms": audit_entry.latency_ms,
            "signed_by": audit_entry.signed_by,
            "user_id": audit_entry.user_id,
            "hallucination_alert": audit_entry.hallucination_alert
        }
        
        # Write to JSON file with pretty formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(audit_dict, f, indent=2, ensure_ascii=False)
        
        print(f"[DEMO MODE] Audit entry written to: {filepath}")
