# Design Document: Aarogya Sahayak

## Overview

Aarogya Sahayak is a serverless, event-driven AI copilot system built on AWS services with local development fallbacks. The architecture follows a three-tier pattern: API Gateway for request handling, Lambda functions for business logic orchestration, and managed services (S3, DynamoDB, OpenSearch) for data persistence. The system integrates Amazon Bedrock for LLM operations (summarization, translation, embeddings) and implements a RAG pipeline using vector similarity search over a curated PMC Open Access corpus.

The design prioritizes safety through multi-layered guardrails: automated PHI detection, confidence-based review flags, hallucination detection via evidence grounding, and comprehensive audit logging. All clinical outputs require explicit clinician review, enforced through the `clinician_review_required` flag on high-risk or low-confidence recommendations.

## Architecture

### High-Level Components

```
┌─────────────┐
│   Client    │ (React SPA)
│  Frontend   │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────────────────────┐
│              API Gateway + Cognito                  │
│  (Authentication, Rate Limiting, Request Validation)│
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│         Lambda: Summarization Handler               │
│  ┌──────────────────────────────────────────────┐  │
│  │ 1. PHI Detection & Validation                │  │
│  │ 2. Amazon Q Orchestration                    │  │
│  │    ├─> Retrieval Service (Vector Search)    │  │
│  │    ├─> Bedrock Summarization                │  │
│  │    ├─> Confidence Scoring                   │  │
│  │    ├─> Hallucination Detection              │  │
│  │    └─> Translation Service                  │  │
│  │ 3. Audit Log Generation                      │  │
│  └──────────────────────────────────────────────┘  │
└──────┬──────────────────────────────────────────────┘
       │
       ├──────────────────┬──────────────────┬─────────┐
       ▼                  ▼                  ▼         ▼
┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐
│  OpenSearch │  │   Bedrock    │  │ DynamoDB │  │   KMS   │
│   Vector    │  │ (LLM + Embed)│  │  Audit   │  │ Secrets │
│   Index     │  │              │  │   Logs   │  │  Keys   │
└─────────────┘  └──────────────┘  └──────────┘  └─────────┘
```

### Component Responsibilities

**API Gateway:**
- JWT token validation via Cognito authorizer
- Request schema validation
- Rate limiting (100 req/user/hour)
- CORS configuration for React SPA

**Lambda Handler (summarize.py):**
- Orchestrates the entire processing pipeline
- Implements PHI detection using regex patterns
- Coordinates Amazon Q workflow steps
- Calculates confidence scores and hallucination flags
- Generates audit log entries with HMAC signatures
- Returns structured JSON response

**Retrieval Service (retrieval.py):**
- Loads vector index from OpenSearch or FAISS
- Generates query embeddings via Bedrock
- Performs cosine similarity search
- Returns top-3 Evidence_Hits per query
- Caches embeddings for demo mode

**Bedrock Client (bedrock_client.py):**
- Abstracts Bedrock API calls
- Provides mock implementations when AWS_MODE=mock
- Functions: get_embeddings(), summarize(), generate_translation()
- Handles retries and error responses

**Amazon Q Orchestrator (q_orchestrator.py):**
- Sequences workflow steps: retrieval → summarization → guardrails → translation
- Manages state between pipeline stages
- Implements circuit breaker for external service failures
- Provides deterministic mock flow for local development

**Frontend (React SPA):**
- Upload page: Clinical note input with character counter
- Results page: Summary display, evidence panel with citations, language switcher
- Audit viewer: Filterable log table with request/response hashes
- Send page: Mock SMS/WhatsApp interface for patient summaries

## Data Models

### Clinical Note Input
```python
{
  "clinical_note": str,  # max 10000 chars
  "language_preference": str,  # default "ta"
  "request_id": str  # UUID v4, optional
}
```

### Action Item
```python
{
  "id": str,  # UUID v4
  "text": str,
  "category": str,  # medication | treatment | diagnostic | lifestyle | followup
  "severity": str,  # low | medium | high | critical
  "confidence": float,  # 0-1, formula: 0.6*max_sim + 0.4*model_score
  "clinician_review_required": bool,
  "evidence": List[EvidenceHit]  # exactly 3 items
}
```

### Evidence Hit
```python
{
  "title": str,
  "pmcid": str,
  "doi": str,
  "snippet": str,  # max 200 chars
  "cosine_similarity": float  # 0-1
}
```

### Audit Log Entry
```python
{
  "timestamp": str,  # ISO 8601
  "request_id": str,  # UUID v4
  "request_hash": str,  # SHA-256
  "response_hash": str,  # SHA-256
  "model_version": str,  # e.g., "anthropic.claude-v2"
  "latency_ms": int,
  "signed_by": str,  # HMAC-SHA256 signature
  "user_id": str,  # from JWT, hashed
  "hallucination_alert": bool
}
```

### Vector Index Document
```python
{
  "doc_id": str,  # PMCID
  "title": str,
  "doi": str,
  "content": str,
  "embedding": List[float],  # 1536-dim for Bedrock embeddings
  "metadata": {
    "publication_date": str,
    "journal": str,
    "authors": List[str]
  }
}
```

## Components and Interfaces

### Bedrock Client Module

**Interface:**
```python
class BedrockClient:
    def __init__(self, aws_mode: str, region: str):
        """Initialize client with mode (production|mock) and AWS region."""
        
    def get_embeddings(self, text: str) -> List[float]:
        """
        Generate 1536-dimensional embeddings for text.
        
        Args:
            text: Input text (max 8000 tokens)
            
        Returns:
            List of 1536 floats representing embedding vector
            
        Raises:
            BedrockError: If API call fails after retries
        """
        
    def summarize(self, clinical_note: str, context: str) -> Dict:
        """
        Generate clinical summary with structured action items.
        
        Args:
            clinical_note: Raw clinical note text
            context: Retrieved evidence context
            
        Returns:
            {
                "summary": str,
                "actions": List[Dict],  # without evidence field
                "model_score": float  # normalized confidence
            }
        """
        
    def generate_translation(self, text: str, target_lang: str) -> str:
        """
        Translate text to target language at 6th-grade reading level.
        
        Args:
            text: Source text in English
            target_lang: "hi" or "ta"
            
        Returns:
            Translated text string
        """
```

**Mock Implementation:**
When `aws_mode="mock"`, returns deterministic responses:
- `get_embeddings()`: Returns random but consistent vector based on text hash
- `summarize()`: Returns template summary with 2 action items
- `generate_translation()`: Returns `f"[{target_lang}] {text}"`

### Retrieval Service Module

**Interface:**
```python
class RetrievalService:
    def __init__(self, index_path: str, bedrock_client: BedrockClient):
        """Load vector index from OpenSearch or FAISS file."""
        
    def search(self, query: str, top_k: int = 3) -> List[EvidenceHit]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default 3)
            
        Returns:
            List of EvidenceHit objects sorted by cosine_similarity desc
            
        Implementation:
            1. Generate query embedding via bedrock_client.get_embeddings()
            2. Compute cosine similarity with all index vectors
            3. Return top_k results with similarity >= 0.0
        """
```

### Confidence Scoring Module

**Interface:**
```python
def calculate_confidence(
    action_item: Dict,
    evidence_hits: List[EvidenceHit],
    model_score: float
) -> float:
    """
    Calculate confidence score using formula:
    confidence = 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
    
    Args:
        action_item: Action item dict (for category check)
        evidence_hits: List of 3 evidence hits
        model_score: Normalized model confidence (0-1), default 0.5
        
    Returns:
        Confidence score in range [0, 1]
        
    Guardrails:
        - If confidence < 0.6: set clinician_review_required = True
        - If category in ['medication', 'treatment']: always set clinician_review_required = True
    """
    max_similarity = max([hit.cosine_similarity for hit in evidence_hits])
    confidence = 0.6 * max_similarity + 0.4 * model_score
    return min(max(confidence, 0.0), 1.0)  # clamp to [0,1]
```

### Hallucination Detection Module

**Interface:**
```python
def detect_hallucination(actions: List[ActionItem]) -> bool:
    """
    Detect potential hallucinations based on evidence grounding.
    
    Args:
        actions: List of ActionItem objects with evidence
        
    Returns:
        True if >30% of actions are poorly grounded, False otherwise
        
    Implementation:
        1. For each action, check if all 3 evidence hits have similarity < 0.75
        2. Count poorly grounded actions
        3. Return (poorly_grounded_count / total_actions) > 0.30
    """
    poorly_grounded = 0
    for action in actions:
        max_sim = max([e.cosine_similarity for e in action.evidence])
        if max_sim < 0.75:
            poorly_grounded += 1
    return (poorly_grounded / len(actions)) > 0.30 if actions else False
```

### PHI Detection Module

**Interface:**
```python
def detect_phi(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential PHI in clinical note using regex patterns.
    
    Args:
        text: Clinical note text
        
    Returns:
        (phi_detected: bool, detected_patterns: List[str])
        
    Patterns checked:
        - Names: Capitalized sequences (Mr./Mrs./Dr. + Name)
        - Dates: MM/DD/YYYY, DD-MM-YYYY formats
        - Phone: (XXX) XXX-XXXX, XXX-XXX-XXXX
        - MRN: "MRN:" followed by digits
        - Addresses: Street numbers + street names
        
    Note: This is a basic heuristic for demo. Production requires NER models.
    """
```

### Amazon Q Orchestrator Module

**Interface:**
```python
class QOrchestrator:
    def __init__(self, bedrock_client: BedrockClient, retrieval_service: RetrievalService):
        """Initialize orchestrator with service dependencies."""
        
    def process_clinical_note(self, clinical_note: str, request_id: str) -> Dict:
        """
        Orchestrate full pipeline: retrieval → summarization → guardrails → translation.
        
        Args:
            clinical_note: Input clinical note
            request_id: UUID for tracking
            
        Returns:
            Complete response dict matching API contract
            
        Pipeline Steps:
            1. Retrieval: Get top-3 evidence for note context
            2. Summarization: Generate summary + action items via Bedrock
            3. Evidence Matching: For each action, retrieve top-3 specific evidence
            4. Confidence Scoring: Calculate confidence for each action
            5. Hallucination Detection: Check overall grounding quality
            6. Translation: Generate Hindi and Tamil patient summaries
            7. Audit Log: Create signed audit entry
        """
```

## Error Handling

### Error Categories and Responses

**Input Validation Errors (HTTP 400):**
- Missing required fields
- Invalid JSON format
- Clinical note exceeds 10000 characters
- Invalid language_preference value

**PHI Detection (HTTP 422):**
- Automated PHI patterns detected
- Response: `{"error": {"code": "PHI_DETECTED", "message": "Potential PHI detected. Please de-identify input.", "details": {"patterns": ["dates", "names"]}}}`

**Authentication Errors (HTTP 401):**
- Missing JWT token
- Expired token
- Invalid signature

**Rate Limiting (HTTP 429):**
- User exceeds 100 requests/hour
- Response includes `Retry-After` header with seconds until reset

**Service Errors (HTTP 500):**
- Bedrock API failures after retries
- OpenSearch connection errors
- DynamoDB write failures
- Logged to CloudWatch with request_id for investigation

### Retry Strategy

**Bedrock API Calls:**
- Exponential backoff: 1s, 2s, 4s
- Max 3 retries
- Timeout: 30s per call

**OpenSearch Queries:**
- Linear backoff: 500ms, 1s
- Max 2 retries
- Fallback to FAISS if OpenSearch unavailable

**DynamoDB Writes:**
- Exponential backoff with jitter
- Max 3 retries
- Non-blocking: Log failure but return response to user

## Testing Strategy

### Unit Tests

**Test Suite: test_summarize.py**

1. `test_summary_schema_validation`: Assert response contains all required keys (summary, patient_summary, actions, sources, confidence, hallucination_alert)

2. `test_action_item_structure`: Assert each action item has id, text, category, severity, confidence, clinician_review_required, evidence array

3. `test_confidence_formula`: Verify confidence = 0.6 * max_sim + 0.4 * model_score for known inputs

4. `test_medication_review_flag`: Assert clinician_review_required=True for category="medication"

5. `test_low_confidence_review_flag`: Assert clinician_review_required=True when confidence < 0.6

**Test Suite: test_retrieval.py**

1. `test_retrieval_top3`: Assert search() returns exactly 3 Evidence_Hits

2. `test_cosine_similarity_range`: Assert all similarity scores in [0, 1]

3. `test_retrieval_sorting`: Assert results sorted by cosine_similarity descending

**Test Suite: test_hallucination.py**

1. `test_hallucination_flag_threshold`: Create actions with 40% poorly grounded, assert hallucination_alert=True

2. `test_hallucination_flag_below_threshold`: Create actions with 20% poorly grounded, assert hallucination_alert=False

**Test Suite: test_phi_detection.py**

1. `test_phi_detection_dates`: Assert detect_phi() returns True for text with dates

2. `test_phi_detection_names`: Assert detect_phi() returns True for text with "Dr. John Smith"

3. `test_phi_detection_clean`: Assert detect_phi() returns False for synthetic note without PHI

### Integration Tests

**Test Suite: test_integration.py**

1. `test_end_to_end_pipeline`: 
   - Load 3 synthetic notes from demo/synthetic_notes/
   - Call POST /summaries for each
   - Assert each response has 3 sources per action
   - Assert patient_summary has both "hi" and "ta" keys
   - Assert processing_time_ms < 20000

2. `test_audit_log_creation`:
   - Submit request
   - Query DynamoDB/local artifacts
   - Assert audit log entry exists with correct request_hash

### Property-Based Tests

Property-based testing will validate universal correctness properties across randomized inputs. Each property test will run minimum 100 iterations with generated test data.

**Testing Framework:** Hypothesis (Python)

**Test Configuration:**
```python
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(max_examples=100)
@given(
    clinical_note=st.text(min_size=50, max_size=1000),
    evidence_hits=st.lists(
        st.builds(EvidenceHit, 
                  cosine_similarity=st.floats(min_value=0.0, max_value=1.0)),
        min_size=3, max_size=3
    )
)
def test_property_name(clinical_note, evidence_hits):
    # Test implementation
    pass
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees. In Aarogya Sahayak, properties validate critical safety constraints, data structure invariants, and business logic rules across all possible inputs.

### Property 1: Response Structure Completeness

*For any* valid clinical note input that successfully generates a summary, the response JSON must contain all required top-level keys (summary, patient_summary, actions, sources, confidence, hallucination_alert), and each action item must contain all required fields (id, text, category, severity, confidence, clinician_review_required, evidence), and each evidence hit must contain all required fields (title, pmcid, doi, snippet, cosine_similarity), and the patient_summary object must contain both "hi" and "ta" language keys.

**Validates: Requirements 1.3, 1.4, 2.2, 3.1, 5.1**

### Property 2: Evidence Cardinality Invariant

*For any* action item in a generated response, the evidence array must contain exactly 3 evidence hits, regardless of the clinical note content or retrieval results.

**Validates: Requirements 2.1**

### Property 3: Confidence Formula Correctness

*For any* action item with known evidence hits and model score, the confidence value must equal 0.6 * max(cosine_similarity of evidence hits) + 0.4 * normalized_model_score, clamped to the range [0, 1].

**Validates: Requirements 4.1**

### Property 4: Low Confidence Review Flag

*For any* action item where the calculated confidence score is below 0.6, the clinician_review_required flag must be set to true.

**Validates: Requirements 4.2**

### Property 5: High-Risk Category Review Flag

*For any* action item where the category is "medication" or "treatment", the clinician_review_required flag must be set to true, regardless of the confidence score.

**Validates: Requirements 4.3**

### Property 6: Poorly Grounded Action Classification

*For any* action item, if all 3 evidence hits have cosine_similarity below 0.75, then that action item should be classified as poorly grounded for hallucination detection purposes.

**Validates: Requirements 2.5**

### Property 7: Hallucination Alert Threshold

*For any* response containing action items, if more than 30% of the action items are poorly grounded (all evidence hits below 0.75 similarity), then the hallucination_alert flag must be set to true.

**Validates: Requirements 2.6**

### Property 8: Patient Summary Sentence Length

*For any* generated patient summary in Hindi or Tamil, the average sentence length must be 15 words or fewer, ensuring 6th-grade reading level accessibility.

**Validates: Requirements 3.2**

### Property 9: PHI Detection and Rejection

*For any* clinical note input containing PHI patterns (names with titles, dates in MM/DD/YYYY format, phone numbers, addresses, or MRN identifiers), the system must reject the request with HTTP 422 status and error code PHI_DETECTED.

**Validates: Requirements 6.3, 8.4**

### Property 10: PHI Pattern Coverage

*For any* clinical note containing patterns matching names (Dr./Mr./Mrs. + capitalized words), dates (MM/DD/YYYY or DD-MM-YYYY), phone numbers ((XXX) XXX-XXXX or XXX-XXX-XXXX), addresses (street numbers + street names), or medical record numbers (MRN: followed by digits), the PHI detection function must identify at least one pattern type.

**Validates: Requirements 6.7**

### Property 11: Audit Log Privacy Preservation

*For any* processed request, the audit log entry must not contain the raw clinical note text or any substring longer than 10 characters from the original input, ensuring PHI is never persisted in logs.

**Validates: Requirements 5.4, 6.4**

### Property 12: Valid Request Success Response

*For any* valid clinical note input (no PHI, valid format, authenticated user, within rate limit), the system must return HTTP 200 status with a response matching the complete response schema.

**Validates: Requirements 8.2**

### Property 13: Invalid Request Error Response

*For any* malformed request (missing required fields, invalid JSON, clinical note exceeding 10000 characters), the system must return HTTP 400 status with error code BAD_REQUEST.

**Validates: Requirements 8.3**

### Property 14: Authentication Failure Response

*For any* request with an invalid JWT token (expired, malformed, or missing), the system must return HTTP 401 status with error code UNAUTHORIZED.

**Validates: Requirements 8.5**

## Security Considerations

### Authentication and Authorization

**JWT Token Validation:**
- All requests to POST /summaries must include valid JWT token in Authorization header
- Token validation checks: signature verification, expiration, issuer claim
- User role extracted from token claims for audit logging
- Failed validation returns 401 with no sensitive information in error message

**Rate Limiting:**
- Implemented at API Gateway level using token bucket algorithm
- Limit: 100 requests per user per hour
- Counter stored in DynamoDB with TTL
- Exceeded limit returns 429 with Retry-After header

**Secrets Management:**
- Production: KMS-encrypted environment variables for Bedrock API keys
- Demo: Plaintext .env file with mock credentials (clearly marked as insecure)
- No secrets in code or CloudFormation templates

### Data Protection

**In Transit:**
- All API communication over HTTPS (TLS 1.2+)
- Certificate validation enforced
- No sensitive data in URL parameters or query strings

**At Rest:**
- DynamoDB audit logs encrypted with AWS-managed keys
- S3 vector index encrypted with SSE-S3
- No PHI stored in any persistent storage

**PHI Detection:**
- Regex-based pattern matching for common PHI types
- Runs before any processing or logging
- False positives acceptable (reject borderline cases)
- Production should use NER models for improved accuracy

### Audit and Compliance

**Tamper Evidence:**
- Each audit log entry signed with HMAC-SHA256
- Signing key derived from KMS master key
- Signature verification available via admin API
- Logs immutable after creation (DynamoDB write-once)

**Audit Trail Contents:**
- Request/response hashes (SHA-256) for integrity verification
- Timestamp, user ID (hashed), model version, latency
- Hallucination alert flag for safety monitoring
- No PHI or raw input text

## Deployment Architecture

### Production (AWS)

```
Internet
   │
   ▼
CloudFront (CDN)
   │
   ├─> S3 (React SPA static files)
   │
   └─> API Gateway
       │
       ├─> Cognito Authorizer (JWT validation)
       │
       └─> Lambda (summarize handler)
           │
           ├─> Bedrock (LLM + embeddings)
           ├─> OpenSearch (vector index)
           ├─> DynamoDB (audit logs)
           └─> KMS (signing keys)
```

**Scaling:**
- Lambda: Auto-scales to 1000 concurrent executions
- OpenSearch: 3-node cluster with read replicas
- DynamoDB: On-demand capacity mode
- API Gateway: 10,000 requests/second burst limit

**Monitoring:**
- CloudWatch metrics: latency, error rate, hallucination_alert frequency
- CloudWatch Logs: Lambda execution logs with request_id correlation
- X-Ray: Distributed tracing for performance debugging
- Alarms: >5% error rate, >10s p99 latency, >20% hallucination rate

### Local Development (Mock Mode)

```
localhost:3000 (React dev server)
   │
   └─> localhost:8000 (Flask/FastAPI local server)
       │
       ├─> Mock Bedrock (deterministic responses)
       ├─> FAISS (local vector index)
       └─> JSON files (demo/_artifacts/)
```

**Setup:**
1. Set `AWS_MODE=mock` in .env
2. Run `python -m src.backend.server` to start local API
3. Run `npm start` in src/frontend/ for React dev server
4. Use demo/demo_run.sh for CLI testing

**Mock Behavior:**
- Bedrock calls return template responses with 2 action items
- Embeddings generated from text hash (consistent but not real)
- Translations return `[lang] original_text` format
- No authentication required (test tokens accepted)
- Audit logs written to demo/_artifacts/audit_logs/

## CI/CD Pipeline

### GitHub Actions Workflow

**Trigger:** Push to main branch or pull request

**Jobs:**

1. **Lint and Format**
   - Run black, flake8, mypy on Python code
   - Run eslint, prettier on TypeScript/React code
   - Fail if any violations

2. **Unit Tests**
   - Run pytest with coverage report
   - Require 80% coverage for src/backend/
   - Upload coverage to Codecov

3. **Integration Tests**
   - Start local mock server
   - Run demo_run.sh with 3 synthetic notes
   - Assert all outputs valid

4. **Security Scan**
   - Run bandit for Python security issues
   - Run npm audit for frontend vulnerabilities
   - Fail on high-severity findings

5. **Build Artifacts**
   - Package Lambda deployment zip
   - Build React production bundle
   - Upload to S3 staging bucket

**Deployment (Manual Approval):**
- Staging: Auto-deploy on main branch merge
- Production: Manual approval required via GitHub environment protection

## Limitations and Future Work

### Current Limitations

1. **Language Support:** Only Hindi and Tamil in demo; production needs 22 Indian languages
2. **Evidence Corpus:** Demo uses 6 PMC articles; production needs 100K+ articles with regular updates
3. **PHI Detection:** Regex-based; production needs NER models for higher accuracy
4. **Model Selection:** Single Bedrock model; production should support model routing based on task
5. **Offline Mode:** Requires internet for Bedrock; future should support edge deployment
6. **Evaluation:** No automated quality metrics; needs BLEU/ROUGE for summaries, retrieval metrics

### Future Enhancements

1. **Multi-Modal Input:** Support for lab reports, imaging notes, prescription images
2. **Longitudinal Summaries:** Track patient history across multiple visits
3. **Differential Diagnosis:** Suggest possible diagnoses with evidence
4. **Drug Interaction Checking:** Integrate with pharmacy databases
5. **Voice Interface:** Speech-to-text for clinical note capture
6. **Federated Learning:** Train on de-identified data from multiple hospitals without centralization
