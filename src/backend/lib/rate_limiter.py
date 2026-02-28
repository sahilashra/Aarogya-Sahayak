"""
Rate Limiting Module for Aarogya Sahayak

Implements rate limiting using DynamoDB with TTL.
Supports both production and mock modes.
"""

import os
import time
from typing import Dict, Optional
from datetime import datetime, timedelta


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class RateLimiter:
    """
    Service for enforcing rate limits on API requests.
    
    In production mode, uses DynamoDB for distributed rate limiting.
    In mock mode, uses in-memory dictionary for development.
    """
    
    def __init__(
        self,
        aws_mode: str = "mock",
        table_name: Optional[str] = None,
        limit: int = 100,
        window_seconds: int = 3600
    ):
        """
        Initialize rate limiter.
        
        Args:
            aws_mode: "mock" or "production"
            table_name: DynamoDB table name (required for production)
            limit: Maximum requests per window
            window_seconds: Time window in seconds (default: 1 hour)
        """
        self.aws_mode = aws_mode
        self.table_name = table_name
        self.limit = limit
        self.window_seconds = window_seconds
        
        # Mock mode storage
        self.mock_counters: Dict[str, Dict] = {}
        
        # Initialize DynamoDB client for production
        if self.aws_mode == "production":
            import boto3
            self.dynamodb = boto3.resource('dynamodb')
            self.table = self.dynamodb.Table(table_name)
    
    def check_rate_limit(self, user_id: str) -> Dict:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
        
        Returns:
            Dict with current_count, limit, reset_time
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if self.aws_mode == "mock":
            return self._check_mock_rate_limit(user_id)
        else:
            return self._check_dynamodb_rate_limit(user_id)
    
    def _check_mock_rate_limit(self, user_id: str) -> Dict:
        """Check rate limit using in-memory storage."""
        current_time = int(time.time())
        
        # Get or create counter
        if user_id not in self.mock_counters:
            self.mock_counters[user_id] = {
                "count": 0,
                "reset_time": current_time + self.window_seconds
            }
        
        counter = self.mock_counters[user_id]
        
        # Reset if window expired
        if current_time >= counter["reset_time"]:
            counter["count"] = 0
            counter["reset_time"] = current_time + self.window_seconds
        
        # Increment counter
        counter["count"] += 1
        
        # Check limit
        if counter["count"] > self.limit:
            retry_after = counter["reset_time"] - current_time
            raise RateLimitExceeded(
                f"Rate limit exceeded. Limit: {self.limit} requests per {self.window_seconds}s. "
                f"Retry after {retry_after} seconds."
            )
        
        return {
            "current_count": counter["count"],
            "limit": self.limit,
            "reset_time": counter["reset_time"],
            "retry_after": counter["reset_time"] - current_time
        }
    
    def _check_dynamodb_rate_limit(self, user_id: str) -> Dict:
        """Check rate limit using DynamoDB."""
        current_time = int(time.time())
        ttl = current_time + self.window_seconds
        
        try:
            # Atomic increment with condition
            response = self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='ADD request_count :inc SET ttl = :ttl, reset_time = if_not_exists(reset_time, :reset)',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':ttl': ttl,
                    ':reset': ttl,
                    ':limit': self.limit
                },
                ConditionExpression='attribute_not_exists(request_count) OR request_count < :limit',
                ReturnValues='ALL_NEW'
            )
            
            item = response['Attributes']
            current_count = int(item['request_count'])
            reset_time = int(item['reset_time'])
            
            return {
                "current_count": current_count,
                "limit": self.limit,
                "reset_time": reset_time,
                "retry_after": max(0, reset_time - current_time)
            }
        
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Rate limit exceeded
            # Fetch current state
            response = self.table.get_item(Key={'user_id': user_id})
            item = response.get('Item', {})
            reset_time = int(item.get('reset_time', current_time + self.window_seconds))
            retry_after = max(0, reset_time - current_time)
            
            raise RateLimitExceeded(
                f"Rate limit exceeded. Limit: {self.limit} requests per {self.window_seconds}s. "
                f"Retry after {retry_after} seconds."
            )
    
    def get_rate_limit_headers(self, user_id: str) -> Dict[str, str]:
        """
        Get rate limit headers for HTTP response.
        
        Args:
            user_id: User identifier
        
        Returns:
            Dict of HTTP headers
        """
        try:
            info = self.check_rate_limit(user_id)
            return {
                "X-RateLimit-Limit": str(self.limit),
                "X-RateLimit-Remaining": str(max(0, self.limit - info["current_count"])),
                "X-RateLimit-Reset": str(info["reset_time"])
            }
        except RateLimitExceeded as e:
            # Return headers even when limit exceeded
            current_time = int(time.time())
            reset_time = current_time + self.window_seconds
            return {
                "X-RateLimit-Limit": str(self.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(self.window_seconds)
            }


def enforce_rate_limit(user_id: str, rate_limiter: RateLimiter) -> Dict[str, str]:
    """
    Enforce rate limit and return headers.
    
    Args:
        user_id: User identifier
        rate_limiter: RateLimiter instance
    
    Returns:
        Dict of rate limit headers
    
    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    info = rate_limiter.check_rate_limit(user_id)
    
    return {
        "X-RateLimit-Limit": str(rate_limiter.limit),
        "X-RateLimit-Remaining": str(max(0, rate_limiter.limit - info["current_count"])),
        "X-RateLimit-Reset": str(info["reset_time"])
    }


# Example usage
if __name__ == "__main__":
    # Mock mode example
    limiter = RateLimiter(aws_mode="mock", limit=5, window_seconds=60)
    
    user_id = "test-user"
    
    # Make requests
    for i in range(7):
        try:
            info = limiter.check_rate_limit(user_id)
            print(f"Request {i+1}: OK - {info['current_count']}/{info['limit']}")
        except RateLimitExceeded as e:
            print(f"Request {i+1}: BLOCKED - {e}")
    
    # Get headers
    headers = limiter.get_rate_limit_headers(user_id)
    print(f"\nRate limit headers: {headers}")
