"""
Authentication Module for Aarogya Sahayak

Handles JWT validation, user authentication, and authorization.
Supports both production (Cognito) and mock modes.
"""

import os
import jwt
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthService:
    """
    Service for handling JWT authentication and validation.
    
    In production mode, validates JWT tokens from AWS Cognito.
    In mock mode, accepts test tokens for development.
    """
    
    def __init__(self, aws_mode: str = "mock", region: str = "us-east-1", user_pool_id: Optional[str] = None):
        """
        Initialize authentication service.
        
        Args:
            aws_mode: "mock" or "production"
            region: AWS region
            user_pool_id: Cognito User Pool ID (required for production)
        """
        self.aws_mode = aws_mode
        self.region = region
        self.user_pool_id = user_pool_id
        
        # Mock mode configuration
        self.mock_secret = "mock-secret-key-for-development-only"
        self.mock_users = {
            "test-clinician": {"role": "clinician", "email": "clinician@example.com"},
            "test-admin": {"role": "admin", "email": "admin@example.com"},
        }
    
    def validate_token(self, authorization_header: Optional[str]) -> Dict:
        """
        Validate JWT token from Authorization header.
        
        Args:
            authorization_header: Authorization header value (e.g., "Bearer <token>")
        
        Returns:
            Dict with user_id, role, email
        
        Raises:
            AuthenticationError: If token is invalid, expired, or missing
        """
        if not authorization_header:
            raise AuthenticationError("Missing Authorization header")
        
        # Extract token from "Bearer <token>" format
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationError("Invalid Authorization header format. Expected 'Bearer <token>'")
        
        token = parts[1]
        
        if self.aws_mode == "mock":
            return self._validate_mock_token(token)
        else:
            return self._validate_cognito_token(token)
    
    def _validate_mock_token(self, token: str) -> Dict:
        """Validate mock JWT token for development."""
        try:
            # Decode without verification for mock mode
            payload = jwt.decode(token, self.mock_secret, algorithms=["HS256"])
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                raise AuthenticationError("Token has expired")
            
            # Extract user info
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing 'sub' claim")
            
            # Get user details from mock database
            user_info = self.mock_users.get(user_id, {})
            
            return {
                "user_id": user_id,
                "role": user_info.get("role", "clinician"),
                "email": user_info.get("email", f"{user_id}@example.com"),
                "issuer": "mock-issuer"
            }
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def _validate_cognito_token(self, token: str) -> Dict:
        """Validate JWT token from AWS Cognito."""
        try:
            # In production, you would:
            # 1. Fetch Cognito public keys from JWKS endpoint
            # 2. Verify token signature using public key
            # 3. Validate issuer, audience, expiration
            
            # For now, decode without verification (placeholder)
            # TODO: Implement full Cognito JWT validation
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Validate issuer
            expected_issuer = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            if payload.get("iss") != expected_issuer:
                raise AuthenticationError("Invalid token issuer")
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                raise AuthenticationError("Token has expired")
            
            # Extract user info
            return {
                "user_id": payload.get("sub"),
                "role": payload.get("custom:role", "clinician"),
                "email": payload.get("email"),
                "issuer": payload.get("iss")
            }
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def generate_mock_token(self, user_id: str, expiration_hours: int = 1) -> str:
        """
        Generate a mock JWT token for testing.
        
        Args:
            user_id: User identifier
            expiration_hours: Token validity in hours
        
        Returns:
            JWT token string
        """
        if self.aws_mode != "mock":
            raise ValueError("Can only generate mock tokens in mock mode")
        
        user_info = self.mock_users.get(user_id, {})
        
        payload = {
            "sub": user_id,
            "email": user_info.get("email", f"{user_id}@example.com"),
            "role": user_info.get("role", "clinician"),
            "iss": "mock-issuer",
            "iat": int(time.time()),
            "exp": int(time.time()) + (expiration_hours * 3600)
        }
        
        return jwt.encode(payload, self.mock_secret, algorithm="HS256")


def extract_user_from_event(event: Dict, auth_service: AuthService) -> Dict:
    """
    Extract and validate user from API Gateway event.
    
    Args:
        event: API Gateway event
        auth_service: AuthService instance
    
    Returns:
        Dict with user_id, role, email
    
    Raises:
        AuthenticationError: If authentication fails
    """
    # Get Authorization header
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization")
    
    # Validate token
    return auth_service.validate_token(auth_header)


# Example usage
if __name__ == "__main__":
    # Mock mode example
    auth = AuthService(aws_mode="mock")
    
    # Generate test token
    token = auth.generate_mock_token("test-clinician", expiration_hours=1)
    print(f"Mock token: {token}")
    
    # Validate token
    user_info = auth.validate_token(f"Bearer {token}")
    print(f"User info: {user_info}")
    
    # Test expired token
    expired_token = auth.generate_mock_token("test-clinician", expiration_hours=-1)
    try:
        auth.validate_token(f"Bearer {expired_token}")
    except AuthenticationError as e:
        print(f"Expected error: {e}")
