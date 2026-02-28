# Limitations and Safety Considerations

## ⚠️ Critical Disclaimer

**Aarogya Sahayak is a non-diagnostic clinical decision support tool.**

This system is intended **solely for research and demonstration purposes**. It is **NOT approved for clinical deployment** or autonomous medical decision-making. All outputs require mandatory clinician review and validation.

---

## Non-Diagnostic Use Only

### What This System IS

- A **clinical decision support tool** that provides evidence-grounded suggestions
- A **research prototype** demonstrating responsible AI practices in healthcare
- An **educational tool** for understanding RAG-based medical AI systems
- A **demonstration** of safety guardrails and human-in-the-loop workflows

### What This System IS NOT

- ❌ **NOT a diagnostic tool** - Cannot diagnose medical conditions
- ❌ **NOT a treatment decision system** - Cannot prescribe or recommend treatments autonomously
- ❌ **NOT a replacement for clinicians** - Requires expert medical oversight
- ❌ **NOT validated for clinical use** - Has not undergone clinical trials or regulatory approval
- ❌ **NOT approved by regulatory bodies** - No FDA, EMA, or equivalent approval

---

## Clinician Oversight Requirement

### Mandatory Human-in-the-Loop

**Every output from this system requires clinician review.** The system enforces this through:

1. **Confidence Scoring**: All action items include explicit confidence scores (0-1 scale)
2. **Review Flags**: Low-confidence items (\u003c0.6) are automatically flagged for review
3. **High-Risk Categories**: Medication and treatment recommendations always require review
4. **Hallucination Detection**: Alerts when \u003e30% of actions are poorly grounded in evidence

### Clinician Responsibilities

Clinicians using this system must:

- ✅ Review all generated summaries and action items
- ✅ Verify evidence citations against original sources
- ✅ Apply clinical judgment to all recommendations
- ✅ Validate appropriateness for specific patient contexts
- ✅ Override or reject suggestions when clinically inappropriate
- ✅ Document their clinical decision-making process

---

## Synthetic Data Limitations

### Demo Data Sources

This demonstration uses **entirely synthetic data**:

- **Clinical Notes**: 3 synthetic cases (diabetes, hypertension, respiratory) created for demo purposes
- **Medical Literature**: 6 synthetic medical literature documents (not real PMC articles)
- **Embeddings**: Generated using mock Bedrock client (not real medical embeddings)

### Implications

- **No Real Patient Data**: System has never processed actual PHI
- **Limited Diversity**: Synthetic notes may not represent real-world clinical complexity
- **Simplified Scenarios**: Demo cases are idealized and lack comorbidities common in practice
- **No Validation**: Outputs have not been validated against real clinical outcomes

### Production Requirements

For clinical deployment, the system would require:

1. **Real PMC Open Access Corpus**: 100,000+ peer-reviewed medical articles
2. **Clinical Validation**: Prospective studies comparing AI suggestions to expert clinicians
3. **Diverse Training Data**: Representative of patient demographics, conditions, and settings
4. **Continuous Updates**: Regular corpus updates to reflect current medical evidence

---

## Language Limitations

### Supported Languages (Demo Scope)

- **Hindi (hi)**: Patient summaries translated to Hindi
- **Tamil (ta)**: Patient summaries translated to Tamil
- **English**: Clinician summaries in English only

### Limitations

- **Limited Language Coverage**: Only 2 of India's 22 scheduled languages supported
- **Translation Quality**: Mock mode uses placeholder translations (not real medical translation)
- **Cultural Adaptation**: No cultural customization of medical terminology or concepts
- **Readability**: 6th-grade reading level target not validated with actual patients

### Production Requirements

For broader deployment:

1. **22+ Indian Languages**: Coverage of all major Indian languages
2. **Professional Medical Translation**: Validated by bilingual medical professionals
3. **Cultural Adaptation**: Terminology adapted to regional medical practices
4. **Readability Testing**: Validated with target patient populations

---

## Regulatory Approval Requirements

### Current Status

- **No Regulatory Approval**: Not submitted to any regulatory body
- **Research Prototype**: Intended for demonstration and research only
- **No Clinical Validation**: No prospective clinical trials conducted

### Required Approvals for Deployment

#### India
- **CDSCO (Central Drugs Standard Control Organization)**: Medical device approval
- **ICMR (Indian Council of Medical Research)**: Clinical trial approval
- **Data Protection**: Compliance with Digital Personal Data Protection Act, 2023

#### International
- **FDA (USA)**: 510(k) clearance or PMA for clinical decision support software
- **CE Mark (Europe)**: Medical Device Regulation (MDR) compliance
- **WHO**: Alignment with WHO guidelines for AI in health

### Validation Requirements

Before clinical deployment:

1. **Clinical Trials**: Randomized controlled trials comparing AI-assisted vs. standard care
2. **Safety Studies**: Adverse event monitoring and reporting
3. **Effectiveness Studies**: Demonstrating improved patient outcomes
4. **Equity Studies**: Ensuring no disparate impact across demographic groups

---

## Data Quality Assumptions and Edge Cases

### Assumptions

The system assumes:

1. **De-identified Input**: Clinical notes are already de-identified (no PHI)
2. **Structured Format**: Notes follow standard clinical documentation format
3. **English Language**: Input clinical notes are in English
4. **Complete Information**: Notes contain sufficient clinical detail for summarization
5. **Accurate Input**: Clinicians have entered accurate clinical observations

### Known Edge Cases

#### Input Edge Cases

- **Very Short Notes** (\u003c100 characters): May not generate meaningful summaries
- **Very Long Notes** (\u003e10,000 characters): Rejected by input validation
- **Non-Medical Text**: System may generate nonsensical outputs for non-clinical input
- **Ambiguous Abbreviations**: May misinterpret context-dependent medical abbreviations
- **Incomplete Notes**: Missing key sections (e.g., no assessment) may produce incomplete summaries

#### Evidence Retrieval Edge Cases

- **Novel Conditions**: Rare diseases may have insufficient evidence in corpus
- **Emerging Treatments**: Recent therapies may not be in literature corpus
- **Contradictory Evidence**: System does not resolve conflicting evidence sources
- **Low-Quality Matches**: All evidence below 0.75 similarity triggers hallucination alert

#### Translation Edge Cases

- **Medical Jargon**: Complex medical terms may not translate accurately
- **Cultural Context**: Western medical concepts may not align with traditional practices
- **Idiomatic Expressions**: Figurative language may be translated literally

### Handling Uncertainty

When the system encounters edge cases:

1. **Low Confidence Scores**: Automatically flags uncertain outputs for review
2. **Hallucination Alerts**: Warns when evidence grounding is weak
3. **Error Responses**: Returns HTTP 400/422/500 for invalid inputs
4. **Audit Logging**: Records all processing attempts for investigation

---

## Technical Limitations

### Model Limitations

- **Mock Mode**: Demo uses deterministic mock responses (not real LLM inference)
- **Embedding Quality**: Mock embeddings are random (not semantically meaningful)
- **Context Window**: Limited to 10,000 characters input
- **No Fine-Tuning**: Generic LLM not specialized for Indian healthcare context

### Infrastructure Limitations

- **No Scalability Testing**: Not tested under production load
- **Single Region**: Demo runs locally (no multi-region deployment)
- **No High Availability**: No redundancy or failover mechanisms
- **Limited Monitoring**: Basic logging only (no comprehensive observability)

### Security Limitations

- **Mock Authentication**: Demo uses hardcoded test tokens (not real Cognito)
- **No Encryption**: Local demo does not encrypt data at rest
- **No Network Security**: No VPC, security groups, or network isolation
- **No Penetration Testing**: Security vulnerabilities not assessed

---

## Ethical Considerations

### Bias and Fairness

- **Training Data Bias**: Synthetic data may not represent diverse populations
- **Language Bias**: Limited to Hindi and Tamil (excludes other Indian languages)
- **Socioeconomic Bias**: Assumes access to smartphones for patient summaries
- **Geographic Bias**: Evidence corpus may be biased toward Western medical practices

### Privacy and Consent

- **PHI Detection**: Regex-based detection may miss some PHI patterns
- **Audit Logs**: Contain hashed data but no mechanism for patient consent
- **Data Retention**: No defined retention or deletion policies
- **Third-Party Services**: Uses AWS Bedrock (data processing outside India)

### Accountability

- **Liability**: Unclear liability framework for AI-generated recommendations
- **Transparency**: Model internals (Bedrock) are not fully transparent
- **Explainability**: Evidence citations provide some explainability but not complete
- **Recourse**: No defined process for contesting or correcting AI outputs

---

## Recommendations for Production Deployment

### Before Clinical Use

1. **Clinical Validation**: Conduct prospective trials in Indian healthcare settings
2. **Regulatory Approval**: Obtain CDSCO and relevant regulatory approvals
3. **Real Data**: Replace synthetic data with validated PMC corpus and real embeddings
4. **Security Hardening**: Implement production-grade authentication, encryption, and monitoring
5. **Bias Auditing**: Conduct comprehensive bias assessment across demographics
6. **Stakeholder Engagement**: Involve clinicians, patients, and ethicists in design

### Continuous Monitoring

1. **Outcome Tracking**: Monitor patient outcomes when AI suggestions are followed
2. **Error Analysis**: Systematically review cases where AI was incorrect
3. **Feedback Loops**: Collect clinician feedback on suggestion quality
4. **Model Updates**: Regularly update evidence corpus and retrain models
5. **Incident Response**: Establish protocols for adverse events related to AI use

---

## Contact and Reporting

For questions, concerns, or to report issues with this system:

- **Project Repository**: [GitHub URL]
- **Issue Tracker**: [GitHub Issues URL]
- **Research Team**: [Contact Email]

---

**Last Updated**: February 2026  
**Version**: 0.1.0 (Demo/Research Prototype)
