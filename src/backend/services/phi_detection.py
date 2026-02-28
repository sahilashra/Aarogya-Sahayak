"""
PHI Detection Module

This module provides functionality to detect Protected Health Information (PHI)
in clinical notes using regex pattern matching. This is a basic heuristic approach
suitable for demo purposes. Production systems should use NER models for improved accuracy.

Detects 11 pattern types: names, dates, phone, mrn, addresses, email, ssn, 
aadhaar, pan_number, ip_address.
"""

import re
from typing import Tuple, List


def detect_phi(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential PHI in clinical note using regex patterns.
    
    This function checks for common PHI patterns including names with titles,
    dates, phone numbers, addresses, and medical record numbers. It uses
    regex-based pattern matching which may produce false positives, but this
    is acceptable for safety-critical applications where rejecting borderline
    cases is preferred.
    
    Args:
        text: Clinical note text to scan for PHI
        
    Returns:
        Tuple containing:
        - phi_detected (bool): True if any PHI pattern is detected
        - detected_patterns (List[str]): List of pattern types found
          (e.g., ["names", "dates", "phone"])
        
    Patterns checked:
        - Names: Capitalized sequences with titles (Dr./Mr./Mrs./Ms. + Name)
        - Dates: MM/DD/YYYY, DD-MM-YYYY, MM-DD-YYYY formats
        - Phone: (XXX) XXX-XXXX, XXX-XXX-XXXX, XXX.XXX.XXXX formats
        - MRN: "MRN:" followed by digits
        - Addresses: Street numbers + street names (e.g., "123 Main Street")
        
    Note: 
        This is a basic heuristic for demo. Production requires NER models
        for higher accuracy and lower false positive rates.
        
    Examples:
        >>> detect_phi("Patient seen on 01/15/2024")
        (True, ['dates'])
        
        >>> detect_phi("Dr. Smith examined the patient")
        (True, ['names'])
        
        >>> detect_phi("Patient has diabetes")
        (False, [])
    """
    detected_patterns = []
    
    # Pattern 1: Names with titles (Dr./Mr./Mrs./Ms. + capitalized words)
    # Matches: "Dr. Smith", "Mrs. Johnson", "Mr. John Doe"
    name_pattern = r'\b(Dr|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*\b'
    if re.search(name_pattern, text):
        detected_patterns.append("names")
    
    # Pattern 2: Dates in various formats
    # MM/DD/YYYY, DD-MM-YYYY, MM-DD-YYYY, DD/MM/YYYY
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # MM/DD/YYYY or DD-MM-YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY-MM-DD
    ]
    for pattern in date_patterns:
        if re.search(pattern, text):
            detected_patterns.append("dates")
            break  # Only add "dates" once
    
    # Pattern 3: Phone numbers in various formats
    # (XXX) XXX-XXXX, XXX-XXX-XXXX, XXX.XXX.XXXX
    phone_patterns = [
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',  # (XXX) XXX-XXXX
        r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',  # XXX-XXX-XXXX or XXX.XXX.XXXX
    ]
    for pattern in phone_patterns:
        if re.search(pattern, text):
            detected_patterns.append("phone")
            break  # Only add "phone" once
    
    # Pattern 4: Medical Record Numbers
    # "MRN:" or "MRN#" followed by digits
    mrn_pattern = r'\bMRN[:#]?\s*\d+'
    if re.search(mrn_pattern, text, re.IGNORECASE):
        detected_patterns.append("mrn")
    
    # Pattern 5: Addresses (street numbers + street names)
    # Matches: "123 Main Street", "456 Oak Ave", "789 First St"
    address_pattern = r'\b\d+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\b'
    if re.search(address_pattern, text):
        detected_patterns.append("addresses")
    
    # Pattern 6: Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    if re.search(email_pattern, text):
        detected_patterns.append("email")
    
    # Pattern 7: US Social Security Numbers (XXX-XX-XXXX)
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    if re.search(ssn_pattern, text):
        detected_patterns.append("ssn")
    
    # Pattern 8: Aadhaar numbers (India) — 12 digits, optional spaces
    aadhaar_pattern = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
    if re.search(aadhaar_pattern, text):
        detected_patterns.append("aadhaar")
    
    # Pattern 9: PAN card numbers (India) — AAAAA9999A
    pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
    if re.search(pan_pattern, text):
        detected_patterns.append("pan_number")
    
    # Pattern 10: Long-form dates — "January 15, 2024" or "15 Jan 2024"
    longdate_pattern = (
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
        r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?'
        r'|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b'
    )
    if re.search(longdate_pattern, text, re.IGNORECASE):
        if "dates" not in detected_patterns:
            detected_patterns.append("dates")
    
    # Pattern 11: IP addresses (can be used to re-identify patients)
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    if re.search(ip_pattern, text):
        detected_patterns.append("ip_address")
    
    # Return True if any patterns detected, along with the list of detected pattern types
    phi_detected = len(detected_patterns) > 0
    
    return phi_detected, detected_patterns
