"""
Unit tests for Lambda summarize handler.

Tests verify request validation, PHI detection, error handling,
and successful response generation.
"""

import json
import pytest
from unittest.mock import Mock, patch
from src.backend.handlers.summarize import lambda_handler


class TestSummarizeHandler:
    """Test suite for Lambda handler functionality."""
    
    def test_missing_clinical_note_field(self):
        """Test that missing clinical_note field returns 400 error."""
        event = {
            "body": json.dumps({
                "language_preference": "ta"
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "clinical_note" in body["error"]["message"]
    
    def test_clinical_note_too_long(self):
        """Test that clinical_note exceeding 10000 chars returns 400 error."""
        event = {
            "body": json.dumps({
                "clinical_note": "x" * 10001
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "10000" in body["error"]["message"]
    
    def test_empty_clinical_note(self):
        """Test that empty clinical_note returns 400 error."""
        event = {
            "body": json.dumps({
                "clinical_note": "   "
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "empty" in body["error"]["message"].lower()
    
    def test_invalid_json_body(self):
        """Test that invalid JSON returns 400 error."""
        event = {
            "body": "not valid json {"
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "JSON" in body["error"]["message"]
    
    def test_invalid_language_preference(self):
        """Test that invalid language_preference returns 400 error."""
        event = {
            "body": json.dumps({
                "clinical_note": "Patient has diabetes",
                "language_preference": "fr"
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "language_preference" in body["error"]["message"]
    
    def test_invalid_request_id_format(self):
        """Test that invalid UUID format for request_id returns 400 error."""
        event = {
            "body": json.dumps({
                "clinical_note": "Patient has diabetes",
                "request_id": "not-a-valid-uuid"
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "request_id" in body["error"]["message"]
    
    def test_phi_detected_returns_422(self):
        """Test that PHI detection returns 422 error."""
        event = {
            "body": json.dumps({
                "clinical_note": "Dr. Smith saw patient on 01/15/2024"
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 422
        body = json.loads(response["body"])
        assert body["error"]["code"] == "PHI_DETECTED"
        assert "patterns" in body["error"]["details"]
    
    def test_clinical_note_not_string(self):
        """Test that non-string clinical_note returns 400 error."""
        event = {
            "body": json.dumps({
                "clinical_note": 12345
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"]["code"] == "BAD_REQUEST"
        assert "string" in body["error"]["message"]
    
    @patch.dict('os.environ', {'AWS_MODE': 'mock', 'AWS_REGION': 'us-east-1'})
    def test_successful_request_returns_200(self):
        """Test that valid request without PHI returns 200 success."""
        event = {
            "body": json.dumps({
                "clinical_note": "Patient presents with type 2 diabetes mellitus. "
                                "Blood glucose levels elevated. Recommend lifestyle modifications "
                                "and metformin therapy. Follow up in 3 months."
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        # Verify response structure
        assert "request_id" in body
        assert "summary" in body
        assert "patient_summary" in body
        assert "actions" in body
        assert "sources" in body
        assert "confidence" in body
        assert "hallucination_alert" in body
        assert "processing_time_ms" in body
        
        # Verify patient_summary has both languages
        assert "hi" in body["patient_summary"]
        assert "ta" in body["patient_summary"]
    
    @patch.dict('os.environ', {'AWS_MODE': 'mock', 'AWS_REGION': 'us-east-1'})
    def test_response_headers_include_cors(self):
        """Test that response includes CORS headers."""
        event = {
            "body": json.dumps({
                "clinical_note": "Patient has hypertension. Blood pressure 140/90."
            })
        }
        
        response = lambda_handler(event, None)
        
        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "Content-Type" in response["headers"]
        assert response["headers"]["Content-Type"] == "application/json"

