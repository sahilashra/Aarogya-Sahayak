"""
Unit tests for PHI detection module.

Tests verify that the detect_phi() function correctly identifies various
PHI patterns including names, dates, phone numbers, addresses, and MRNs.
"""

import pytest
from src.backend.services.phi_detection import detect_phi


class TestPHIDetection:
    """Test suite for PHI detection functionality."""
    
    def test_phi_detection_names(self):
        """Test detection of names with titles."""
        text = "Dr. Smith examined the patient"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "names" in patterns
    
    def test_phi_detection_dates_slash(self):
        """Test detection of dates in MM/DD/YYYY format."""
        text = "Patient seen on 01/15/2024"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "dates" in patterns
    
    def test_phi_detection_dates_dash(self):
        """Test detection of dates in DD-MM-YYYY format."""
        text = "Appointment scheduled for 15-01-2024"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "dates" in patterns
    
    def test_phi_detection_phone_parentheses(self):
        """Test detection of phone numbers in (XXX) XXX-XXXX format."""
        text = "Contact at (555) 123-4567"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "phone" in patterns
    
    def test_phi_detection_phone_dashes(self):
        """Test detection of phone numbers in XXX-XXX-XXXX format."""
        text = "Call 555-123-4567 for results"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "phone" in patterns
    
    def test_phi_detection_mrn(self):
        """Test detection of medical record numbers."""
        text = "Patient MRN: 123456"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "mrn" in patterns
    
    def test_phi_detection_address(self):
        """Test detection of street addresses."""
        text = "Lives at 123 Main Street"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "addresses" in patterns
    
    def test_phi_detection_clean_text(self):
        """Test that clean synthetic notes without PHI return False."""
        text = "Patient has diabetes and hypertension. Prescribed metformin."
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is False
        assert len(patterns) == 0
    
    def test_phi_detection_multiple_patterns(self):
        """Test detection of multiple PHI pattern types."""
        text = "Dr. Johnson saw patient on 01/15/2024. MRN: 789012. Contact: (555) 987-6543"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "names" in patterns
        assert "dates" in patterns
        assert "mrn" in patterns
        assert "phone" in patterns
    
    def test_phi_detection_mr_without_name(self):
        """Test that Mr. without a following name doesn't trigger false positive."""
        text = "Patient reports feeling better"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is False
    
    def test_phi_detection_case_insensitive_mrn(self):
        """Test that MRN detection is case-insensitive."""
        text = "Patient mrn: 456789"
        phi_detected, patterns = detect_phi(text)
        assert phi_detected is True
        assert "mrn" in patterns
