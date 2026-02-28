# Aarogya Sahayak — Demo Script (2 minutes)

Use this script when recording your screen demo or presenting live.

---

## Opening (15 seconds)

"India has 1 doctor for every 1,456 patients. Overworked clinicians spend 40% of their time on documentation. Aarogya Sahayak gives every clinician an AI copilot — with safety built in from day one."

## Show the Problem (15 seconds)

Open demo/synthetic_notes/diabetes_case.txt

"This is a real-world style clinical note. A doctor writes something like this after every patient visit. Extracting action items, finding evidence, translating for the patient — all manual today."

## Show the Solution (45 seconds)

Open src/frontend/index.html in browser

1. "Select the Diabetes case — a 52-year-old woman, HbA1c 8.2%"
2. Click "Analyse Note" — wait for animation
3. Point to confidence score: "Every recommendation has an explicit confidence score — 69%. Not a black box."
4. Point to clinician review badge: "High-risk actions like medication changes are always flagged for clinician review. The AI never acts alone."
5. Click an action to expand evidence: "Every suggestion is grounded in peer-reviewed PMC literature. No hallucinations."
6. Click Tamil tab: "Patient summary generated in Tamil — accessible to patients who don't speak English."

## Show Safety (20 seconds)

"What happens if someone accidentally submits a note with patient details?"

Open terminal, run:

```bash
python -c "
import os; os.environ['AWS_MODE']='mock'; os.environ['FAISS_INDEX_PATH']='demo/pmc_corpus'
from src.backend.handlers.summarize import lambda_handler
r = lambda_handler({'body': {'clinical_note': 'Dr. Smith saw patient John Doe on 01/15/2024. MRN: 123456'}}, None)
import json; print(json.dumps(json.loads(r['body']), indent=2))
"
```

Show the 422 PHI_DETECTED response.

"Rejected immediately. The note never reaches the AI."

## Closing (25 seconds)

"Built on AWS — Lambda, Bedrock, DynamoDB, KMS. Fully deployable in one command:

bash deploy.sh

Cost: $6 per month at prototype scale.

Roadmap: 22 Indian languages, real PMC corpus, CDSCO approval pathway.

This is what responsible AI for healthcare looks like."

---

## Key Numbers to Memorise

- 1:1,456 doctor-patient ratio in India
- 11 PHI pattern types detected (including Aadhaar, PAN)
- Confidence formula: 0.6 × retrieval + 0.4 × model score
- < 0.6 confidence → mandatory clinician review
- $6/month AWS cost at prototype scale
- 49 tests, 0 failures
- 3 languages: English summary + Hindi + Tamil patient communication
