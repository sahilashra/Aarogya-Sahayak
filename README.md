# Aarogya Sahayak 🏥
**Clinical AI Copilot for Responsible Decision Support — Built for India**

> ⚠️ **Non-Diagnostic Prototype** — All AI outputs require mandatory review by a qualified clinician. Not approved for clinical use.

---

## 🇮🇳 The Problem

India has **1 doctor per 1,456 patients** (WHO recommends 1:1,000). Overworked clinicians spend 30–40% of their time on documentation and evidence lookup. Rural healthcare workers often lack access to specialist knowledge and must communicate in Hindi or Tamil — not English.

**Aarogya Sahayak** gives every clinician an AI copilot that:
- Generates structured clinical summaries from raw notes in seconds
- Surfaces evidence-grounded action items from peer-reviewed PMC literature
- Communicates findings to patients in **Hindi and Tamil**
- Operates with explicit safety guardrails: PHI detection, confidence scoring, hallucination guard, and tamper-evident audit logging

---

## 🌐 Live Demo

| Resource | URL |
|----------|-----|
| **Frontend (S3)** | http://aarogya-frontend-761341390248.s3-website-us-east-1.amazonaws.com |
| **API Endpoint** | `POST https://1iewiqgxm1.execute-api.us-east-1.amazonaws.com/summaries` |

**Try it:**
```bash
curl -X POST https://1iewiqgxm1.execute-api.us-east-1.amazonaws.com/summaries \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "52-year-old female with Type 2 Diabetes. Fasting glucose 186 mg/dL. HbA1c 8.2%.",
    "language_preference": "hi"
  }'
```

---

## 🤖 Why AI Is Required

Manual clinical note review is slow, inconsistent, and unavailable in regional languages. AI enables:

- Instant structured summarisation of unstructured clinical text
- Evidence-grounded recommendations (RAG over PubMed/PMC corpus)
- Hindi and Tamil patient summaries for health literacy in rural India
- Confidence scoring to flag when clinician review is mandatory — automatically

Without AI, this pipeline requires trained clinicians per note. That does not scale for 1.4 billion people.

---

## ☁️ AWS Architecture

```
Clinical Note (text / PDF)
        │
        ▼
  API Gateway ──► AWS Lambda Handler
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     PHI Check    Titan Embeddings  Nova Pro LLM
     (block PII)  (vectorise note)  (summarise)
                        │             │
                        ▼             ▼
                  FAISS Search    Hindi / Tamil
                  (S3 corpus)     Translation
                        │             │
                        └──────┬──────┘
                               ▼
                      Confidence Score
                      Hallucination Guard
                      HMAC-Signed Audit Log (DynamoDB)
                               │
                               ▼
                         JSON Response
```

| AWS Service | How Used |
|-------------|----------|
| **Amazon Bedrock — Nova Pro** | Clinical summarisation + multilingual translation |
| **Amazon Bedrock — Titan Embeddings V1** | Semantic vector embeddings for RAG |
| **AWS Lambda** | Serverless inference handler (zero idle cost) |
| **Amazon API Gateway** | REST endpoint with request validation |
| **Amazon S3** | FAISS index + PMC corpus storage |
| **Amazon DynamoDB** | Tamper-evident audit log per inference |
| **AWS CloudFormation** | Full infrastructure-as-code deployment |
| **Kiro IDE** | Spec-driven development throughout |

---

## 🛡️ Safety Guardrails

### 1. PHI Detection (blocks before processing)
11 pattern types: names, dates, phone numbers, MRN, addresses, email, Aadhaar, PAN, SSN, long-form dates, IP addresses. Any PHI → HTTP 422, request never processed, never logged.

### 2. Confidence Scoring (explicit, auditable)
```
confidence = 0.6 × max_retrieval_similarity + 0.4 × model_score
```
Below 0.6 → `clinician_review_required: true` automatically.

### 3. Hallucination Guard
If >30% of generated actions cannot be grounded in PMC evidence → `hallucination_alert: true`, actions suppressed.

### 4. Tamper-Evident Audit Logs
Every request generates an HMAC-SHA256 signed audit entry in DynamoDB. Raw clinical text is **never stored** — only SHA-256 hash.

---

## ✨ What Makes This Different

| Feature | Aarogya Sahayak | Generic LLM Chatbot |
|---------|-----------------|---------------------|
| Evidence grounding | ✅ RAG from PMC literature | ❌ Hallucinated |
| Confidence scoring | ✅ Explicit formula, auditable | ❌ None |
| PHI protection | ✅ 11-pattern detection, hard block | ❌ None |
| Audit trail | ✅ HMAC-signed, tamper-evident | ❌ None |
| Indian languages | ✅ Hindi + Tamil | ❌ English only |
| Clinician review gates | ✅ Automatic flagging | ❌ None |
| Hallucination detection | ✅ Evidence similarity threshold | ❌ None |
| PDF upload | ✅ In-browser extraction, no server upload | ❌ N/A |

---

## 🧪 Test Results

```
Unit Tests:         49 / 49 passed   ✅  (1.14s)
Production API:      8 / 8 passed    ✅  (avg 7.5s warm)
Frontend UI:         7 / 7 passed    ✅
Overall:            64 / 65 passed   ✅  98.5% pass rate
```

Coverage: handlers 90% · orchestrator 93% · PHI detection 84% · models 100%

---

## 🚀 Quick Start — Run Locally (No AWS Needed)

```bash
git clone https://github.com/sahilashra/Aarogya-Sahayak.git
cd Aarogya-Sahayak

python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Build demo corpus (mock mode — no AWS)
python demo/build_corpus.py

# Run demo
python demo/demo_run.py

# Open UI
start src/frontend/index.html   # Windows
open src/frontend/index.html    # Mac
```

Everything runs in mock mode locally. No AWS credentials, no internet required.

---

## 📋 API Reference

**POST** `/summaries`

```json
{
  "clinical_note": "string (required, max 10,000 chars)",
  "language_preference": "hi | ta | en (optional, default hi)",
  "request_id": "uuid (optional)"
}
```

**Response:**
```json
{
  "request_id": "550e8400-...",
  "summary": "Structured clinical summary...",
  "patient_summary": {
    "hi": "हिन्दी में सारांश...",
    "ta": "தமிழில் சுருக்கம்..."
  },
  "actions": [
    {
      "text": "Initiate Metformin therapy",
      "category": "medication",
      "severity": "high",
      "confidence": 0.79,
      "clinician_review_required": true,
      "evidence": [
        {
          "title": "Evidence-Based Management of Type 2 Diabetes",
          "pmcid": "PMC8901234",
          "cosine_similarity": 0.71
        }
      ]
    }
  ],
  "confidence": 0.72,
  "hallucination_alert": false,
  "processing_time_ms": 4974
}
```

**Error codes:**
- `422` — PHI detected in input
- `400` — Validation failure (missing field, note too long/short, invalid language)

---

## 📁 Project Structure

```
Aarogya-Sahayak/
├── src/
│   ├── backend/
│   │   ├── handlers/summarize.py          # Lambda entry point
│   │   ├── services/
│   │   │   ├── phi_detection.py           # 11-pattern PHI scanner
│   │   │   ├── retrieval.py               # FAISS vector search + S3
│   │   │   ├── confidence_scoring.py      # Explicit confidence formula
│   │   │   ├── hallucination_detection.py
│   │   │   ├── audit_logger.py            # HMAC-signed audit logs
│   │   │   └── q_orchestrator.py          # Pipeline orchestration
│   │   ├── lib/
│   │   │   ├── bedrock_client.py          # Bedrock + mock client
│   │   │   ├── auth.py                    # JWT / Cognito auth
│   │   │   └── rate_limiter.py            # DynamoDB rate limiting
│   │   └── models.py                      # Pydantic data models
│   └── frontend/index.html                # Single-file demo UI
├── tests/                                 # 49 unit tests
├── demo/
│   ├── synthetic_notes/                   # 3 de-identified cases
│   ├── pmc_corpus/                        # FAISS index (6 docs)
│   ├── build_corpus.py                    # Corpus index builder
│   ├── demo_run.py                        # Local demo runner
│   └── DEMO_SCRIPT.md                     # Step-by-step demo guide
├── infrastructure/
│   ├── cloudformation-minimal.yaml        # Hackathon stack
│   └── cloudformation.yaml               # Full production stack
├── deploy.sh                              # One-command AWS deploy
├── walkthrough.md                         # Full regression test report
├── limitations.md                         # Honest limitations
├── bias_audit_plan.md                     # Responsible AI audit plan
└── .env.example                           # Config template
```

---

## 🚀 AWS Deployment

```bash
# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-minimal.yaml \
  --stack-name aarogya-sahayak-hackathon \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

| Service | Cost/month |
|---------|-----------|
| Lambda (10K requests) | ~$0.25 |
| Bedrock Nova Pro (summaries) | ~$3.50 |
| Bedrock Titan Embeddings | ~$0.05 |
| DynamoDB (PAY_PER_REQUEST) | ~$0.01 |
| API Gateway | ~$0.01 |
| S3 + CloudWatch | ~$0.52 |
| **Total** | **~$4.34/month** |

$240 credits ≈ 55 months of operation at prototype scale.

---

## 🔮 Roadmap

**Immediate next (post-hackathon):**
- **OCR for scanned lab reports** — currently processes text-native PDFs to reduce data entry to zero; next step is Tesseract/AWS Textract integration for scanned documents
- **EHR sync** — write action items directly into patient charts via HL7 FHIR API (eliminates copy-paste from AI to EMR)
- **NER-based PHI detection** via AWS Comprehend Medical (replacing regex for higher recall)

**Medium term:**
- 22 Indian languages via IndicTrans2
- 100K+ PMC articles in corpus (vs 6 today)
- Drug interaction checking via DrugBank API
- Voice input for clinical note capture (Whisper-based)

**Long term:**
- Longitudinal patient summaries across visits
- CDSCO regulatory approval pathway
- Federated deployment for hospital networks

---

## ⚠️ Limitations

See [limitations.md](limitations.md) for full details.

- Regex-based PHI detection (NER recommended for production)
- 6-document PMC corpus (synthetic — not validated on real clinical outcomes)
- Hindi + Tamil only (22-language roadmap planned)
- Not approved by any regulatory body (CDSCO, FDA, etc.)
- `auth.py` and `rate_limiter.py` — 0% test coverage (not wired in hackathon build)
- Cold start latency ~10s (use provisioned concurrency for production)

---

## 📊 Test & Validation Report

See [walkthrough.md](walkthrough.md) for the full regression test report including:
- 49 unit test results with coverage breakdown
- 8 live production API test cases
- 7 frontend UI test cases with screenshots
- Known bugs and risk assessment

---

*Built for AI for Bharath Hackathon — February 2026*
*Powered by Amazon Bedrock Nova Pro + Titan Embeddings + FAISS RAG + AWS Lambda*
