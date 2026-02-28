"""
Lambda Handler for Clinical Note Summarization

This module implements the POST /summaries endpoint handler for processing
clinical notes through the Aarogya Sahayak pipeline. It handles request
validation, PHI detection, orchestration, and error responses.
"""

import json
import uuid
import os
import traceback
from typing import Dict, Any, Optional

from src.backend.services.phi_detection import detect_phi
from src.backend.services.q_orchestrator import QOrchestrator
from src.backend.lib.bedrock_client import BedrockClient
from src.backend.services.retrieval import RetrievalService


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for POST /summaries endpoint.
    
    This function processes clinical notes through the full Aarogya Sahayak
    pipeline, including PHI detection, RAG-based summarization, confidence
    scoring, hallucination detection, and multilingual translation.
    
    Args:
        event: API Gateway event dict containing:
            - body: JSON string with clinical_note, language_preference, request_id
            - headers: HTTP headers (for authentication in production)
            - requestContext: Request metadata
        context: Lambda context object (unused in current implementation)
        
    Returns:
        API Gateway response dict with:
            - statusCode: HTTP status code
            - headers: Response headers (CORS, Content-Type)
            - body: JSON string with response or error
            
    Error Codes:
        - 400 BAD_REQUEST: Invalid request format or missing fields
        - 422 PHI_DETECTED: PHI patterns detected in input
        - 401 UNAUTHORIZED: Invalid or missing JWT token (production only)
        - 429 RATE_LIMIT: Rate limit exceeded (production only)
        - 500 INTERNAL_ERROR: Server error
        
    Requirements:
        Implements Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.7
    """
    try:
        # Parse and validate request body
        validation_result = _parse_request_body(event)
        
        # Check if validation returned an error response
        if "statusCode" in validation_result and validation_result["statusCode"] != 200:
            return validation_result  # Return error response
        
        # Extract validated request data
        request_data = validation_result
        clinical_note = request_data["clinical_note"]
        language_preference = request_data.get("language_preference", "ta")
        request_id = request_data.get("request_id")
        
        # Run PHI detection
        phi_detected, detected_patterns = detect_phi(clinical_note)
        if phi_detected:
            return _create_error_response(
                status_code=422,
                error_code="PHI_DETECTED",
                message="Potential PHI detected in input. Please de-identify the clinical note before submission.",
                details={"patterns": detected_patterns}
            )
        
        # Initialize services
        aws_mode = os.environ.get("AWS_MODE", "mock")
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        
        bedrock_client = BedrockClient(aws_mode=aws_mode, region=aws_region)
        
        # Initialize retrieval service with FAISS index
        index_path = os.environ.get("FAISS_INDEX_PATH", "demo/pmc_corpus/faiss_index.bin")
        retrieval_service = RetrievalService(index_path=index_path, bedrock_client=bedrock_client)
        
        # Initialize orchestrator
        orchestrator = QOrchestrator(
            bedrock_client=bedrock_client,
            retrieval_service=retrieval_service,
            aws_mode=aws_mode
        )
        
        # Process clinical note through pipeline
        response_data = orchestrator.process_clinical_note(
            clinical_note=clinical_note,
            request_id=request_id,
            language_preference=language_preference
        )
        
        # Return success response
        return _create_success_response(response_data)
        
    except ValueError as e:
        # Validation errors
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message=str(e)
        )
    except Exception as e:
        # Internal server errors
        print(f"Internal error: {e}")
        print(traceback.format_exc())
        return _create_error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="An internal error occurred while processing your request.",
            details={"error_type": type(e).__name__}
        )


def _parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and validate request body from API Gateway event.
    
    Args:
        event: API Gateway event dict
        
    Returns:
        Dict with parsed request data or error response dict
        
    Validation Rules:
        - Body must be valid JSON
        - clinical_note field is required
        - clinical_note must not exceed 10000 characters
        - language_preference must be "ta" or "hi" if provided
        - request_id must be valid UUID v4 if provided
    """
    # Extract body from event
    body = event.get("body", "")
    
    # Handle case where body is already a dict (for local testing)
    if isinstance(body, dict):
        request_data = body
    else:
        # Parse JSON body
        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return _create_error_response(
                status_code=400,
                error_code="BAD_REQUEST",
                message="Invalid JSON in request body."
            )
    
    # Validate required fields
    if "clinical_note" not in request_data:
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Missing required field: clinical_note"
        )
    
    clinical_note = request_data["clinical_note"]
    
    # Validate clinical_note is a string
    if not isinstance(clinical_note, str):
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Field 'clinical_note' must be a string."
        )
    
    # Validate clinical_note length
    if len(clinical_note) > 10000:
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Field 'clinical_note' exceeds maximum length of 10000 characters.",
            details={"length": len(clinical_note), "max_length": 10000}
        )
    
    # Validate clinical_note is not empty
    if not clinical_note.strip():
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Field 'clinical_note' cannot be empty."
        )
    
    # Validate language_preference if provided
    language_preference = request_data.get("language_preference", "ta")
    if language_preference not in ["ta", "hi"]:
        return _create_error_response(
            status_code=400,
            error_code="BAD_REQUEST",
            message="Field 'language_preference' must be 'ta' or 'hi'.",
            details={"provided": language_preference, "allowed": ["ta", "hi"]}
        )
    
    # Validate request_id if provided
    request_id = request_data.get("request_id")
    if request_id is not None:
        try:
            # Validate UUID format
            uuid.UUID(request_id, version=4)
        except (ValueError, AttributeError):
            return _create_error_response(
                status_code=400,
                error_code="BAD_REQUEST",
                message="Field 'request_id' must be a valid UUID v4.",
                details={"provided": request_id}
            )
    
    return request_data


def _create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create successful API Gateway response.
    
    Args:
        data: Response data dict
        
    Returns:
        API Gateway response dict with status 200
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # CORS
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(data)
    }


def _create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create error API Gateway response.
    
    Args:
        status_code: HTTP status code
        error_code: Error code string (BAD_REQUEST, PHI_DETECTED, etc.)
        message: Human-readable error message
        details: Optional additional error details
        
    Returns:
        API Gateway response dict with error
    """
    error_body = {
        "error": {
            "code": error_code,
            "message": message
        }
    }
    
    if details:
        error_body["error"]["details"] = details
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # CORS
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(error_body)
    }
