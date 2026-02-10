# Requirements Document

## Introduction

Aarogya Sahayak is an enterprise AI copilot system designed to support healthcare delivery in Primary Health Centers (PHCs) and hospitals across India. The system generates clinician-ready summaries from clinical notes, provides RAG-grounded evidence from medical literature, produces multilingual patient education materials, and maintains audit-grade safety guardrails. The system addresses the critical need for clinical decision support in resource-constrained settings while ensuring responsible AI practices through confidence scoring, human-in-the-loop workflows, and comprehensive audit trails. This is a non-diagnostic clinical decision support tool that requires clinician oversight for all outputs.

## Glossary

- **System**: The Aarogya Sahayak AI copilot platform
- **Clinician**: Healthcare provider using the system (doctor, nurse practitioner, or medical officer)
- **Clinical_Note**: De-identified or synthetic patient encounter documentation
- **RAG**: Retrieval-Augmented Generation - evidence retrieval from medical literature
- **Bedrock**: Amazon Bedrock LLM service for text generation and embeddings
- **Amazon_Q**: AWS orchestration service for workflow coordination
- **Evidence_Hit**: Retrieved medical literature citation with relevance score and cosine similarity
- **Confidence_Score**: Numerical value [0,1] calculated as 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
- **PHI**: Protected Health Information - must never be stored or logged
- **Audit_Log**: Tamper-evident record of system operations without PHI, signed with HMAC
- **Regional_Language**: Tamil (fixed for demo scope)
- **Action_Item**: Structured clinical recommendation with id, text, category, severity, confidence, clinician_review_required flag, and evidence sources
- **Guardrail**: Safety mechanism preventing unsafe or low-confidence outputs
- **Similarity_Threshold**: Cosine similarity threshold of 0.75 for evidence grounding
- **Hallucination_Alert**: Flag set to true when >30% of Action_Items have max similarity < 0.75
- **Request_Hash**: SHA-256 hash of input Clinical_Note for audit trail
- **Response_Hash**: SHA-256 hash of output JSON for audit trail

## Non-Goals and Explicit Limitations

1. This System is NOT a diagnostic tool and SHALL NOT be used for autonomous medical diagnosis
2. This System SHALL NOT replace clinician judgment or clinical workflows
3. This System SHALL NOT process real patient PHI during development or demo phases
4. This System SHALL NOT provide treatment decisions without mandatory clinician review
5. This System SHALL NOT guarantee medical accuracy - all outputs require clinical validation
6. This System SHALL NOT be deployed in production without regulatory review and approval
7. This System SHALL NOT support languages beyond Hindi and Tamil in demo scope

## Functional Requirements

### Requirement 1: Clinical Summary Generation

**User Story:** As a clinician, I want to receive concise summaries of clinical notes, so that I can quickly understand patient status and make informed decisions.

#### Acceptance Criteria

1. WHEN a Clinical_Note is submitted to POST /summaries, THE System SHALL generate a clinician-ready summary containing between 3 and 8 sentences
2. WHEN generating summaries, THE System SHALL complete processing within 20 seconds for demo datasets
3. WHEN a summary is generated, THE System SHALL return a JSON response containing keys: summary, patient_summary, actions, sources, confidence, and hallucination_alert
4. WHEN the summary is created, THE System SHALL extract structured Action_Items where each contains: id, text, category, severity, confidence, clinician_review_required, and evidence array
5. THE System SHALL use Bedrock for text generation when AWS credentials are configured
6. WHEN AWS credentials are unavailable, THE System SHALL use deterministic mock implementations

### Requirement 2: Evidence Retrieval and Grounding

**User Story:** As a clinician, I want each clinical recommendation backed by medical literature, so that I can trust the system's suggestions and verify claims.

#### Acceptance Criteria

1. WHEN generating Action_Items, THE System SHALL retrieve and return the top 3 Evidence_Hits from the PMC Open Access corpus using vector similarity search
2. WHEN an Evidence_Hit is returned, THE System SHALL include title, pmcid, doi, snippet, and cosine_similarity fields
3. WHEN retrieval is performed, THE System SHALL use Bedrock embeddings or local FAISS index for vector search
4. WHEN calculating similarity, THE System SHALL use cosine similarity metric with Similarity_Threshold of 0.75
5. WHEN an Action_Item has all Evidence_Hits with cosine_similarity below 0.75, THE System SHALL mark that Action_Item as poorly grounded
6. IF more than 30 percent of Action_Items are poorly grounded, THEN THE System SHALL set hallucination_alert to true in the response
7. THE System SHALL prefer OpenSearch vector plugin for production and provide FAISS fallback for local demo

### Requirement 3: Multilingual Patient Communication

**User Story:** As a clinician, I want patient-friendly summaries in Hindi and Tamil, so that I can communicate effectively with patients in their preferred language.

#### Acceptance Criteria

1. WHEN a summary is generated, THE System SHALL produce a patient_summary object containing hi and ta language keys
2. WHEN generating patient summaries, THE System SHALL produce text at 6th-grade reading level with sentence length under 15 words average
3. WHEN Bedrock translation services are configured, THE System SHALL use Bedrock for Hindi and Tamil translation
4. WHEN Bedrock is unavailable, THE System SHALL use deterministic mock translations with language-tagged placeholders
5. THE System SHALL use Tamil as the fixed Regional_Language for demo scope

### Requirement 4: Confidence Scoring and Guardrails

**User Story:** As a clinician, I want to know when the system is uncertain, so that I can apply appropriate clinical judgment and avoid unsafe recommendations.

#### Acceptance Criteria

1. WHEN an Action_Item is generated, THE System SHALL calculate Confidence_Score using the formula: confidence = 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
2. IF an Action_Item has Confidence_Score below 0.6, THEN THE System SHALL set clinician_review_required to true
3. WHEN an Action_Item category is medication or treatment, THE System SHALL always set clinician_review_required to true regardless of confidence
4. THE System SHALL document the confidence scoring formula in code docstrings with parameter explanations
5. WHEN normalized_model_score is unavailable from Bedrock, THE System SHALL use 0.5 as default value
6. THE System SHALL ensure all Confidence_Score values are in range [0, 1]

### Requirement 5: Audit Trail and Logging

**User Story:** As a system administrator, I want comprehensive audit logs of all system operations, so that I can ensure accountability and investigate issues without compromising patient privacy.

#### Acceptance Criteria

1. WHEN a summarization request is processed, THE System SHALL create an Audit_Log entry with fields: timestamp, request_id, request_hash, response_hash, model_version, latency_ms, and signed_by
2. WHEN creating request_hash, THE System SHALL compute SHA-256 hash of the input Clinical_Note
3. WHEN creating response_hash, THE System SHALL compute SHA-256 hash of the output JSON
4. THE System SHALL NOT include any PHI or raw input text in Audit_Log entries
5. WHEN using DynamoDB for storage, THE System SHALL write audit entries atomically with response generation
6. WHEN running in local demo mode, THE System SHALL write Audit_Log entries as JSON files to demo/_artifacts/audit_logs/
7. THE System SHALL sign audit log entries with HMAC-SHA256 using KMS-derived key for tamper evidence
8. THE System SHALL provide a log viewer interface in the frontend for audit review with filtering by date and request_id

### Requirement 6: Data Privacy and PHI Protection

**User Story:** As a compliance officer, I want the system to detect and reject PHI, so that we maintain patient privacy and regulatory compliance at all times.

#### Acceptance Criteria

1. THE System SHALL use only PMC Open Access subset, NFHS public statistics, MIMIC demo data, or fully synthetic Clinical_Notes for development and demo
2. WHEN a Clinical_Note is received, THE System SHALL run automated PHI detection before processing
3. IF PHI is detected in input, THEN THE System SHALL reject the request with HTTP 422 status and error code PHI_DETECTED
4. THE System SHALL NOT store or log raw input text containing potential PHI
5. THE System SHALL include data source documentation in README and limitations.md
6. THE System SHALL provide clear disclaimers in README stating synthetic-data-only policy for demo
7. WHEN PHI detection is performed, THE System SHALL check for patterns matching names, dates, phone numbers, addresses, and medical record numbers

### Requirement 7: AWS Service Integration

**User Story:** As a developer, I want seamless integration with Amazon Bedrock and Amazon Q, so that I can leverage enterprise-grade AI services with local fallbacks for development.

#### Acceptance Criteria

1. WHEN AWS credentials are configured in environment, THE System SHALL use Bedrock for embeddings, summarization, and translation
2. WHEN AWS credentials are unavailable, THE System SHALL use deterministic mock implementations returning valid response structures
3. THE System SHALL provide bedrock_client module with functions: get_embeddings, summarize, and generate_translation
4. THE System SHALL provide q_orchestrator module emulating Amazon Q workflow orchestration for sequencing retrieval, summarization, and guardrail checks
5. WHEN using vector search in production, THE System SHALL use OpenSearch vector plugin
6. WHEN running local demo, THE System SHALL use FAISS index for vector search
7. THE System SHALL clearly separate AWS mode from mock mode using environment variable AWS_MODE with values production or mock

### Requirement 8: API Contract and Interface Design

**User Story:** As a frontend developer, I want a well-defined API contract with explicit schemas, so that I can build reliable user interfaces for clinicians.

#### Acceptance Criteria

1. THE System SHALL expose POST /summaries endpoint accepting JSON request body with clinical_note field
2. WHEN a valid request is received, THE System SHALL return HTTP 200 with JSON response matching the response schema
3. WHEN request validation fails, THE System SHALL return HTTP 400 with error code BAD_REQUEST
4. WHEN PHI is detected, THE System SHALL return HTTP 422 with error code PHI_DETECTED
5. WHEN authentication fails, THE System SHALL return HTTP 401 with error code UNAUTHORIZED
6. WHEN rate limit is exceeded, THE System SHALL return HTTP 429 with error code RATE_LIMIT
7. WHEN internal errors occur, THE System SHALL return HTTP 500 with error code INTERNAL_ERROR
8. THE System SHALL provide React SPA frontend with pages: Upload, Results, Language Switcher, Audit Viewer, and Send
9. WHEN displaying results, THE Frontend SHALL show summary, evidence panel with clickable citations, and multilingual patient summaries
10. THE System SHALL provide demo_run.sh script for local CLI execution of 3 synthetic notes

### Requirement 9: Security and Authentication

**User Story:** As a security engineer, I want role-based access control and secure authentication, so that only authorized clinicians can access the system.

#### Acceptance Criteria

1. THE System SHALL use Cognito for user authentication and JWT token issuance
2. THE System SHALL support two roles: clinician and admin
3. WHEN a request is received, THE System SHALL validate JWT token and extract user role
4. THE System SHALL enforce rate limiting of 100 requests per user per hour
5. WHEN rate limit is exceeded, THE System SHALL return HTTP 429 with retry-after header
6. THE System SHALL use KMS for encryption key management in production
7. WHEN running in local demo mode, THE System SHALL use mock authentication with hardcoded test tokens
8. THE System SHALL log all authentication failures to audit trail

### Requirement 10: Testing and Validation

**User Story:** As a quality assurance engineer, I want comprehensive test coverage with explicit assertions, so that I can verify system correctness and catch regressions.

#### Acceptance Criteria

1. THE System SHALL include unit test test_summary_schema_validation verifying response contains keys: summary, patient_summary, actions, sources, confidence, hallucination_alert
2. THE System SHALL include unit test test_action_item_structure verifying each Action_Item contains: id, text, category, severity, confidence, clinician_review_required, evidence
3. THE System SHALL include unit test test_retrieval_top3 verifying retrieval returns exactly 3 Evidence_Hits per Action_Item
4. THE System SHALL include unit test test_confidence_formula verifying confidence calculation matches formula: 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
5. THE System SHALL include unit test test_hallucination_flag verifying hallucination_alert is true when >30% of Action_Items have max similarity < 0.75
6. WHEN demo_run.sh is executed, THE System SHALL process 3 synthetic Clinical_Notes end-to-end
7. WHEN integration tests run, THE System SHALL verify each result includes exactly 3 sources per Action_Item and both hi and ta language summaries
8. THE System SHALL include GitHub Actions CI workflow running pytest on push to main branch
9. THE System SHALL achieve minimum 80% code coverage for core modules: summarize, retrieval, confidence_scoring

### Requirement 11: Infrastructure and Deployment

**User Story:** As a DevOps engineer, I want infrastructure-as-code templates with clear separation of environments, so that I can deploy the system consistently and securely.

#### Acceptance Criteria

1. THE System SHALL provide CloudFormation or CDK templates defining API Gateway, Lambda, S3, DynamoDB, Cognito, and KMS resources
2. THE System SHALL include .env.example file with placeholder variables: AWS_REGION, AWS_MODE, BEDROCK_MODEL_ID, COGNITO_USER_POOL_ID, KMS_KEY_ID
3. WHEN deploying to production, THE Infrastructure SHALL use Cognito for authentication and KMS for secrets management
4. WHEN running local demo, THE System SHALL write artifacts to demo/_artifacts/ directory
5. THE System SHALL document S3 bucket structure for storing PMC corpus embeddings and audit logs
6. THE System SHALL use environment variable AWS_MODE to switch between production and mock modes
7. THE System SHALL provide deployment documentation in README with step-by-step AWS setup instructions

### Requirement 11: Responsible AI Documentation

**User Story:** As a clinical safety officer, I want explicit documentation of system limitations and bias considerations, so that I can ensure safe and ethical deployment.

#### Acceptance Criteria

1. THE System SHALL include limitations.md documenting clinical-use disclaimers and regulatory constraints
2. THE System SHALL include bias_audit_plan.md placeholder for bias assessment procedures
3. THE System SHALL include prominent safety disclaimers in README about non-diagnostic use
4. THE System SHALL document all assumptions about data quality and model limitations
5. WHEN presenting results, THE System SHALL clearly indicate that outputs require clinician review and are not autonomous medical decisions


### Requirement 12: Responsible AI and Safety Documentation

**User Story:** As a clinical safety officer, I want explicit documentation of system limitations and bias considerations, so that I can ensure safe and ethical deployment.

#### Acceptance Criteria

1. THE System SHALL include limitations.md documenting: non-diagnostic use only, clinician oversight required, synthetic data limitations, language limitations, and regulatory approval requirements
2. THE System SHALL include bias_audit_plan.md placeholder with sections for: demographic bias assessment, language bias evaluation, and evidence source diversity analysis
3. THE System SHALL include prominent safety disclaimers in README stating: "This is a non-diagnostic clinical decision support tool. All outputs require clinician review and validation. Not approved for autonomous medical decision-making."
4. THE System SHALL document all assumptions about data quality, model limitations, and edge cases in limitations.md
5. WHEN presenting results in frontend, THE System SHALL display disclaimer banner: "Requires clinician review - not for autonomous use"
6. THE System SHALL include data source attribution in README for PMC Open Access, NFHS, and MIMIC datasets

## API Contract

### POST /summaries

**Request Schema:**
```json
{
  "clinical_note": "string (required, max 10000 characters)",
  "language_preference": "string (optional, default: 'ta', enum: ['ta'])",
  "request_id": "string (optional, UUID v4)"
}
```

**Success Response (HTTP 200):**
```json
{
  "request_id": "string (UUID v4)",
  "summary": "string (3-8 sentences)",
  "patient_summary": {
    "hi": "string (Hindi, 6th-grade level)",
    "ta": "string (Tamil, 6th-grade level)"
  },
  "actions": [
    {
      "id": "string (UUID v4)",
      "text": "string",
      "category": "string (enum: medication, treatment, diagnostic, lifestyle, followup)",
      "severity": "string (enum: low, medium, high, critical)",
      "confidence": "number (0-1, formula: 0.6*max_sim + 0.4*model_score)",
      "clinician_review_required": "boolean",
      "evidence": [
        {
          "title": "string",
          "pmcid": "string",
          "doi": "string",
          "snippet": "string (max 200 chars)",
          "cosine_similarity": "number (0-1)"
        }
      ]
    }
  ],
  "sources": [
    {
      "title": "string",
      "pmcid": "string",
      "doi": "string",
      "snippet": "string",
      "cosine_similarity": "number (0-1)"
    }
  ],
  "confidence": "number (0-1, overall confidence)",
  "hallucination_alert": "boolean",
  "processing_time_ms": "number"
}
```

**Error Response Schema:**
```json
{
  "error": {
    "code": "string (enum: BAD_REQUEST, PHI_DETECTED, UNAUTHORIZED, RATE_LIMIT, INTERNAL_ERROR)",
    "message": "string",
    "details": "object (optional)"
  }
}
```

**Error Codes:**
- `BAD_REQUEST` (HTTP 400): Invalid request format or missing required fields
- `PHI_DETECTED` (HTTP 422): Potential PHI detected in input, request rejected
- `UNAUTHORIZED` (HTTP 401): Invalid or missing JWT token
- `RATE_LIMIT` (HTTP 429): Rate limit exceeded, includes retry-after header
- `INTERNAL_ERROR` (HTTP 500): Server error, logged for investigation

## Confidence Scoring Formula

**Formula:**
```
confidence = 0.6 * max_retrieval_similarity + 0.4 * normalized_model_score
```

**Parameters:**
- `max_retrieval_similarity`: Maximum cosine similarity among top-3 Evidence_Hits for the Action_Item (range: 0-1)
- `normalized_model_score`: Bedrock model confidence score normalized to [0,1], default 0.5 if unavailable

**Guardrail Rules:**
1. IF `confidence < 0.6` THEN `clinician_review_required = true`
2. IF `category IN ['medication', 'treatment']` THEN `clinician_review_required = true` (always)
3. IF `max_retrieval_similarity < 0.75` THEN Action_Item is poorly grounded

## Hallucination Detection Rules

**Rule:**
```
IF (count of poorly grounded Action_Items / total Action_Items) > 0.30
THEN hallucination_alert = true
```

**Poorly Grounded Definition:**
An Action_Item where all 3 Evidence_Hits have `cosine_similarity < 0.75`

**Similarity Threshold:** 0.75 (cosine similarity)

## Demo Scope and Assumptions

1. **Demo Data:** 3 synthetic clinical notes provided in demo/synthetic_notes/
2. **Evidence Corpus:** 6 PMC Open Access articles seeded in demo/pmc_corpus/
3. **Languages:** Hindi (hi) and Tamil (ta) only
4. **Mock Mode:** When AWS_MODE=mock, all Bedrock calls return deterministic responses
5. **Performance:** Demo must complete in <20 seconds per note on local machine
6. **Authentication:** Demo uses hardcoded test JWT tokens, no real Cognito
7. **Storage:** Demo writes to demo/_artifacts/ instead of S3/DynamoDB
8. **Limitations:** Not validated for clinical use, synthetic data only, requires regulatory approval before production deployment
