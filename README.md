# Aarogya Sahayak 🏥🤖
**Enterprise AI Copilot for Responsible Clinical Decision Support**

Aarogya Sahayak is a **non-diagnostic, safety-first AI copilot** designed to assist clinicians by generating concise clinical summaries, evidence-grounded action items, and multilingual patient-friendly explanations — while enforcing strict privacy, auditability, and responsible AI guardrails.

This project demonstrates how **healthcare AI can be built responsibly**, with explicit confidence scoring, hallucination detection, PHI protection, and human-in-the-loop workflows.

> ⚠️ **Important**: This system is NOT a diagnostic tool.  
> All outputs require clinician review and validation.

---

## ✨ Key Features

- 🩺 **Clinician-Ready Summaries**
  - 3–8 sentence summaries from clinical notes
  - Structured action items with severity, category, and confidence

- 📚 **RAG-Grounded Evidence**
  - Retrieval-Augmented Generation using PMC Open Access literature
  - Top-3 evidence hits per action item
  - Cosine similarity thresholding to detect weak grounding

- 🌍 **Multilingual Patient Communication**
  - Patient summaries in **Hindi** and **Tamil**
  - 6th-grade readability for accessibility

- 🛡️ **Responsible AI Guardrails**
  - Explicit confidence scoring formula
  - Hallucination detection based on evidence similarity
  - Mandatory clinician review for low-confidence or high-risk actions

- 🔒 **Privacy & Compliance by Design**
  - Automated PHI detection and rejection
  - No storage or logging of raw clinical text
  - Tamper-evident audit logs with cryptographic signatures

- 🧪 **Deterministic Mock Mode**
  - Fully runnable without AWS credentials
  - Reproducible demos using synthetic data only

---

## 🏗️ High-Level Architecture

```
Client (React SPA)
        |
        v
API Gateway + Cognito (Auth, Rate Limits)
        |
        v
Lambda (Summarization Handler)
  ├─ PHI Detection
  ├─ RAG Retrieval (OpenSearch / FAISS)
  ├─ Bedrock Summarization
  ├─ Confidence Scoring
  ├─ Hallucination Detection
  ├─ Translation (Hindi, Tamil)
  └─ Audit Logging (HMAC-signed)
```

**AI Services:** Amazon Bedrock  
**Vector Search:** OpenSearch (prod) / FAISS (local)  
**Storage:** DynamoDB, S3  
**Security:** Cognito, KMS  

---

## 🧠 How Safety Is Enforced

Safety is enforced through **explicit, testable rules**:

### Confidence Formula
```
confidence = 0.6 * max_retrieval_similarity
           + 0.4 * normalized_model_score
```

### Clinician Review Rules
- Confidence < 0.6 → clinician review required
- Medication or treatment actions → clinician review required (always)

### Hallucination Detection
- If >30% of action items have all evidence similarity < 0.75
- → `hallucination_alert = true`

### PHI Protection
- Regex-based PHI detection (demo scope)
- Requests rejected with HTTP 422 if PHI detected
- No raw clinical text stored or logged

---

## 📡 API Overview

### POST /summaries

**Request**
```json
{
  "clinical_note": "string (max 10000 chars)",
  "language_preference": "ta",
  "request_id": "UUID (optional)"
}
```

**Response**
```json
{
  "summary": "Clinician summary",
  "patient_summary": {
    "hi": "Hindi explanation",
    "ta": "Tamil explanation"
  },
  "actions": [
    {
      "text": "Action item",
      "category": "medication | treatment | lifestyle | followup",
      "severity": "low | medium | high | critical",
      "confidence": 0.82,
      "clinician_review_required": true,
      "evidence": [ ... ]
    }
  ],
  "hallucination_alert": false,
  "confidence": 0.78
}
```

---

## 🧪 Testing & Correctness

- Unit tests for:
  - Schema validation
  - Confidence calculation
  - Hallucination detection
  - PHI detection
- Integration tests:
  - End-to-end pipeline on synthetic notes
- Property-based tests (Hypothesis):
  - Safety invariants
  - Evidence cardinality
  - Confidence bounds
- CI via **GitHub Actions**
  - Linting, tests, security scans
  - ≥80% backend coverage enforced

---

## 🚀 Running Locally (Mock Mode)

### Prerequisites
- Python 3.10+
- Node.js 18+

### Steps
```bash
# Backend
export AWS_MODE=mock
python -m src.backend.server

# Frontend
cd src/frontend
npm install
npm start
```

Or run:
```bash
./demo/demo_run.sh
```

✔ Uses synthetic data  
✔ No AWS credentials required  
✔ Deterministic outputs  

---

## 📁 Project Structure

```
src/
 ├─ backend/
 │   ├─ summarize.py
 │   ├─ retrieval.py
 │   ├─ confidence.py
 │   ├─ phi_detection.py
 │   └─ q_orchestrator.py
 ├─ frontend/
 │   └─ React SPA
demo/
 ├─ synthetic_notes/
 ├─ pmc_corpus/
 └─ _artifacts/
```

---

## 🚧 Limitations

- Synthetic data only (no real PHI)
- Hindi + Tamil only (demo scope)
- Regex-based PHI detection (NER recommended for production)
- Not approved for clinical deployment
- Not validated against real-world outcomes

---

## 🔮 Future Work

- Support for 22+ Indian languages
- Multimodal inputs (labs, prescriptions)
- Longitudinal patient summaries
- Drug interaction checks
- Voice-based clinical note capture

---

## 📜 Disclaimer

**Aarogya Sahayak is a non-diagnostic clinical decision support tool.**  
It is intended for research and demonstration purposes only.  
All outputs require clinician review and are **not** approved for autonomous medical use.
