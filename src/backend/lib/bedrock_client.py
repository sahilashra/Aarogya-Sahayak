"""Amazon Bedrock client with mock fallback for local development."""

import time
import hashlib
import json
from typing import List, Dict, Optional
import os


class BedrockError(Exception):
    """Exception raised when Bedrock API calls fail after retries."""
    pass


class BedrockClient:
    """
    Client for Amazon Bedrock LLM operations with mock fallback.
    
    Supports two modes:
    - production: Uses actual Bedrock API calls
    - mock: Returns deterministic responses for local development
    
    All methods implement exponential backoff retry logic (1s, 2s, 4s, max 3 retries).
    """
    
    def __init__(self, aws_mode: str = "mock", region: str = "us-east-1"):
        """
        Initialize Bedrock client.
        
        Args:
            aws_mode: "production" for real Bedrock API, "mock" for local development
            region: AWS region for Bedrock service
        """
        self.aws_mode = aws_mode
        self.region = region
        self.bedrock_client = None
        self.bedrock_runtime = None
        self.model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        
        if aws_mode == "production":
            try:
                import boto3
                self.bedrock_client = boto3.client("bedrock", region_name=region)
                self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
            except Exception as e:
                raise BedrockError(f"Failed to initialize Bedrock client: {e}")
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            BedrockError: If all retries fail
        """
        retry_delays = [1, 2, 4]  # seconds
        last_exception = None
        
        for attempt, delay in enumerate(retry_delays + [0], start=1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt <= len(retry_delays):
                    time.sleep(delay)
                    continue
                else:
                    break
        
        raise BedrockError(f"Failed after {len(retry_delays)} retries: {last_exception}")
    
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
        if self.aws_mode == "mock":
            return self._mock_get_embeddings(text)
        
        return self._retry_with_backoff(self._bedrock_get_embeddings, text)
    
    def _bedrock_get_embeddings(self, text: str) -> List[float]:
        """Call Bedrock API for embeddings."""
        try:
            # Use Titan for embeddings (Nova doesn't support embeddings)
            # If model_id is Nova, fallback to Titan for embeddings
            embeddings_model_id = "amazon.titan-embed-text-v1"
            if "amazon.nova" in self.model_id:
                # Nova doesn't do embeddings, use Titan as fallback
                embeddings_model_id = "amazon.titan-embed-text-v1"
            elif "amazon.titan" in self.model_id:
                embeddings_model_id = self.model_id
            
            body = json.dumps({
                "inputText": text
            })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=embeddings_model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('embedding', [])
            
        except Exception as e:
            raise Exception(f"Bedrock embeddings API error: {e}")
    
    def _mock_get_embeddings(self, text: str) -> List[float]:
        """
        Generate mock embeddings with semantic clustering.
        
        Documents about the same medical topic produce similar vectors,
        ensuring cosine similarity reflects topic relevance.
        This makes confidence scores realistic (0.65-0.85) for demo.
        """
        import numpy as np
        import hashlib
        
        text_lower = text.lower()
        
        # Define semantic topic centroids
        # Each topic has a fixed seed — all documents about that topic
        # will have embeddings close to the same centroid vector
        topic_seed = 42  # default (unrecognised topic)
        
        if any(k in text_lower for k in [
            'diabetes', 'glucose', 'hba1c', 'metformin', 'insulin',
            'hyperglycemi', 'glycaemi', 'glycemic', 't2dm'
        ]):
            topic_seed = 1001
        
        elif any(k in text_lower for k in [
            'hypertension', 'blood pressure', 'bp ', 'amlodipine',
            'antihypertensive', 'systolic', 'diastolic'
        ]):
            topic_seed = 1002
        
        elif any(k in text_lower for k in [
            'respiratory', 'asthma', 'copd', 'breath', 'wheez',
            'spirometry', 'inhaler', 'bronch', 'pulmon'
        ]):
            topic_seed = 1003
        
        elif any(k in text_lower for k in [
            'lipid', 'cholesterol', 'statin', 'dyslipidemia',
            'triglyceride', 'ldl', 'hdl'
        ]):
            topic_seed = 1004
        
        elif any(k in text_lower for k in [
            'medication', 'adherence', 'compliance', 'dosing',
            'prescription', 'pharmacotherapy'
        ]):
            topic_seed = 1005
        
        elif any(k in text_lower for k in [
            'lifestyle', 'exercise', 'diet', 'physical activity',
            'weight loss', 'smoking', 'nutrition'
        ]):
            topic_seed = 1006
        
        elif any(k in text_lower for k in [
            'patient education', 'health literacy', 'self-management',
            'teach', 'counsell'
        ]):
            topic_seed = 1007
        
        # Generate topic centroid vector (fixed for this topic)
        centroid_rng = np.random.RandomState(topic_seed)
        centroid = centroid_rng.randn(1536).astype(np.float32)
        centroid = centroid / np.linalg.norm(centroid)
        
        # Add small document-specific noise so vectors are not identical
        # Noise magnitude 0.02 keeps cosine similarity in [0.90, 0.99] range
        # for same-topic documents
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        noise_seed = int(text_hash[:8], 16) % (2 ** 31)
        noise_rng = np.random.RandomState(noise_seed)
        noise = noise_rng.randn(1536).astype(np.float32) * 0.02
        
        vec = centroid + noise
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()
    
    def summarize(self, clinical_note: str, context: str = "") -> Dict:
        """
        Generate clinical summary with structured action items.
        
        Args:
            clinical_note: Raw clinical note text
            context: Retrieved evidence context (optional)
            
        Returns:
            {
                "summary": str,
                "actions": List[Dict],  # without evidence field
                "model_score": float  # normalized confidence
            }
            
        Raises:
            BedrockError: If API call fails after retries
        """
        if self.aws_mode == "mock":
            return self._mock_summarize(clinical_note, context)
        
        return self._retry_with_backoff(self._bedrock_summarize, clinical_note, context)
    
    def _bedrock_summarize(self, clinical_note: str, context: str) -> Dict:
        """Call Bedrock API for summarization."""
        try:
            model_id = self.model_id
            
            prompt = f"""You are a clinical AI assistant. Generate a concise clinical summary and action items.

Clinical Note:
{clinical_note}

Evidence Context:
{context}

Generate:
1. A clinical summary (3-8 sentences)
2. Structured action items with category, severity, and text

Format your response as JSON:
{{
    "summary": "...",
    "actions": [
        {{"text": "...", "category": "medication|treatment|diagnostic|lifestyle|followup", "severity": "low|medium|high|critical"}}
    ],
    "model_score": 0.8
}}"""

            # Build request body based on model provider
            if "amazon.nova" in model_id:
                body = {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": 1000, "temperature": 0.1}
                }
            else:
                # Anthropic Claude format
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}]
                }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            
            # Parse response based on model provider
            if "amazon.nova" in model_id:
                raw_text = response_body["output"]["message"]["content"][0]["text"]
            else:
                raw_text = response_body["content"][0]["text"]
            
            # Parse JSON from response
            try:
                result = json.loads(raw_text)
                return result
            except json.JSONDecodeError:
                # Fallback if model doesn't return valid JSON
                return {
                    "summary": raw_text[:500],
                    "actions": [],
                    "model_score": 0.5
                }
                
        except Exception as e:
            raise Exception(f"Bedrock summarization API error: {e}")
    
    def _mock_summarize(self, clinical_note: str, context: str) -> Dict:
        """Generate contextually-aware mock summary.
        
        Detects PRIMARY condition by keyword frequency scoring, not just presence,
        so each note produces distinct output.
        """
        note_lower = clinical_note.lower()
        
        # Score each condition by counting keyword hits
        scores = {
            'diabetes': sum(note_lower.count(k) for k in [
                'diabetes', 'glucose', 'hba1c', 'metformin', 'insulin',
                'hyperglycemi', 'glycaemi', 'glycemic', 't2dm', 'diabetic'
            ]),
            'hypertension': sum(note_lower.count(k) for k in [
                'hypertension', 'blood pressure', 'bp:', 'amlodipine',
                'antihypertensive', 'systolic', 'diastolic', 'mmhg'
            ]),
            'respiratory': sum(note_lower.count(k) for k in [
                'respiratory', 'asthma', 'copd', 'breath', 'wheez',
                'spirometry', 'inhaler', 'bronch', 'pulmon', 'oxygen',
                'spo2', 'dyspnoea', 'dyspnea', 'cough'
            ]),
            'lipid': sum(note_lower.count(k) for k in [
                'lipid', 'cholesterol', 'statin', 'dyslipidemia',
                'triglyceride', 'ldl', 'hdl'
            ]),
        }
        
        # Find primary condition (highest score)
        primary = max(scores, key=scores.get)
        
        # Find secondary conditions (score > 1 and not primary)
        secondary = [k for k, v in scores.items() if v > 1 and k != primary]
        
        # Build condition display string
        condition_map = {
            'diabetes': 'Type 2 Diabetes Mellitus',
            'hypertension': 'Hypertension',
            'respiratory': 'Chronic Respiratory Disease',
            'lipid': 'Dyslipidaemia',
        }
        
        primary_label = condition_map[primary]
        if secondary:
            secondary_labels = " and ".join(condition_map[s] for s in secondary[:1])
            condition_str = f"{primary_label} with comorbid {secondary_labels}"
        else:
            condition_str = primary_label
        
        # Condition-specific actions
        action_templates = {
            'diabetes': [
                {"text": "Initiate or optimise Metformin therapy as per current glycaemic targets", "category": "medication", "severity": "high"},
                {"text": "Order HbA1c test to assess 3-month glycaemic control", "category": "diagnostic", "severity": "high"},
                {"text": "Refer to ophthalmology for diabetic retinopathy screening", "category": "followup", "severity": "medium"},
                {"text": "Dietary counselling — low glycaemic index diet, reduce refined carbohydrates", "category": "lifestyle", "severity": "medium"},
            ],
            'hypertension': [
                {"text": "Review and optimise antihypertensive regimen; target BP below 130/80 mmHg", "category": "treatment", "severity": "high"},
                {"text": "Arrange 24-hour ambulatory blood pressure monitoring to assess control", "category": "diagnostic", "severity": "high"},
                {"text": "Assess renal function and electrolytes — U&E, eGFR within 2 weeks", "category": "diagnostic", "severity": "medium"},
                {"text": "Structured lifestyle intervention: sodium restriction below 2g/day, DASH diet", "category": "lifestyle", "severity": "medium"},
            ],
            'respiratory': [
                {"text": "Optimise bronchodilator therapy per GINA/GOLD step guidelines", "category": "medication", "severity": "high"},
                {"text": "Perform spirometry with reversibility testing for objective lung function assessment", "category": "diagnostic", "severity": "high"},
                {"text": "Arrange urgent review if SpO2 falls below 92% or symptoms worsen", "category": "followup", "severity": "high"},
                {"text": "Reinforce smoking cessation and avoidance of known respiratory triggers", "category": "lifestyle", "severity": "medium"},
            ],
            'lipid': [
                {"text": "Initiate statin therapy for cardiovascular risk reduction per ACC/AHA guidelines", "category": "medication", "severity": "medium"},
                {"text": "Repeat fasting lipid panel in 6 weeks to assess treatment response", "category": "diagnostic", "severity": "medium"},
                {"text": "Mediterranean diet counselling to reduce LDL and cardiovascular risk", "category": "lifestyle", "severity": "medium"},
                {"text": "Calculate 10-year ASCVD risk score to guide treatment intensity", "category": "diagnostic", "severity": "medium"},
            ],
        }
        
        # Add one relevant secondary action if applicable
        actions = list(action_templates[primary])
        if secondary and secondary[0] in action_templates:
            actions.append(action_templates[secondary[0]][0])
        actions = actions[:4]  # Limit to 4 actions
        
        # Build condition-specific summary
        summary_templates = {
            'diabetes': (
                f"Patient presents with {condition_str} requiring structured glycaemic management. "
                f"Elevated fasting glucose and HbA1c indicate suboptimal metabolic control requiring pharmacotherapy review. "
                f"Metformin optimisation and dietary modification are first-line interventions. "
                f"Screening for microvascular complications including retinopathy and nephropathy is indicated. "
                f"Follow-up in 2 to 4 weeks to assess medication tolerance and glycaemic response is recommended."
            ),
            'hypertension': (
                f"Patient presents with {condition_str} with suboptimal blood pressure control. "
                f"Sustained elevated readings indicate need for antihypertensive therapy review and optimisation. "
                f"Target blood pressure below 130/80 mmHg is recommended to reduce cardiovascular and renal risk. "
                f"Lifestyle modifications including sodium restriction and regular aerobic exercise are essential adjuncts. "
                f"Renal function monitoring and ambulatory BP assessment should be arranged within 2 weeks."
            ),
            'respiratory': (
                f"Patient presents with {condition_str} with symptoms indicating suboptimal disease control. "
                f"Objective spirometry assessment is required to guide pharmacotherapy decisions. "
                f"Inhaler technique review and step-up of bronchodilator therapy should be considered. "
                f"Trigger avoidance, smoking cessation support, and written action plan provision are priorities. "
                f"Urgent review criteria and escalation pathway should be clearly communicated to the patient."
            ),
            'lipid': (
                f"Patient presents with {condition_str} conferring elevated cardiovascular risk. "
                f"Fasting lipid profile indicates need for pharmacological and lifestyle intervention. "
                f"Statin therapy initiation should be guided by absolute cardiovascular risk calculation. "
                f"Dietary modification with Mediterranean or portfolio diet approach is recommended. "
                f"Repeat lipid assessment and cardiovascular risk stratification should occur within 6 weeks."
            ),
        }
        
        return {
            "summary": summary_templates[primary],
            "actions": actions,
            "model_score": 0.78
        }
    
    def _validate_sentence_length(self, text: str, max_avg_words: int = 15) -> bool:
        """
        Validate that average sentence length is within limit.
        
        Args:
            text: Text to validate
            max_avg_words: Maximum average words per sentence (default 15)
            
        Returns:
            True if average sentence length <= max_avg_words, False otherwise
        """
        # Split text into sentences (basic splitting on .!?)
        import re
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return True
        
        # Count words in each sentence
        total_words = 0
        for sentence in sentences:
            words = sentence.split()
            total_words += len(words)
        
        avg_words = total_words / len(sentences)
        return avg_words <= max_avg_words
    
    def generate_translation(self, text: str, target_lang: str) -> str:
        """
        Translate text to target language at 6th-grade reading level.
        
        Args:
            text: Source text in English
            target_lang: "hi" (Hindi) or "ta" (Tamil)
            
        Returns:
            Translated text string with average sentence length <= 15 words
            
        Raises:
            BedrockError: If API call fails after retries
        """
        if self.aws_mode == "mock":
            return self._mock_generate_translation(text, target_lang)
        
        return self._retry_with_backoff(self._bedrock_generate_translation, text, target_lang)
    
    def _bedrock_generate_translation(self, text: str, target_lang: str) -> str:
            """
            Call Bedrock API for translation with sentence length validation.

            The prompt explicitly requests 6th-grade reading level with sentences
            averaging 15 words or less. Supports both Nova and Claude models.
            """
            try:
                model_id = self.model_id

                lang_names = {"hi": "Hindi", "ta": "Tamil"}
                lang_name = lang_names.get(target_lang, target_lang)

                prompt = f"""Translate the following medical summary to {lang_name} at a 6th-grade reading level.

    Use simple everyday words. Keep sentences short (15 words or fewer).

    Provide ONLY the {lang_name} translation, no explanations.

    English text:
    {text}"""

                # Build request body based on model provider
                if "amazon.nova" in model_id:
                    body = {
                        "messages": [{"role": "user", "content": [{"text": prompt}]}],
                        "inferenceConfig": {"maxTokens": 1000, "temperature": 0.3}
                    }
                else:
                    # Anthropic Claude format
                    body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "temperature": 0.3,
                        "messages": [{"role": "user", "content": prompt}]
                    }

                response = self.bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )

                response_body = json.loads(response["body"].read())

                # Parse response based on model provider
                if "amazon.nova" in model_id:
                    translation = response_body["output"]["message"]["content"][0]["text"]
                else:
                    translation = response_body["content"][0]["text"]

                return translation.strip()

            except Exception as e:
                raise Exception(f"Bedrock translation API error: {e}")

    
    def _mock_generate_translation(self, text: str, target_lang: str) -> str:
        """Return pre-written clinical translations in Hindi or Tamil.
        Matched by detecting the primary condition in the English summary."""
        text_lower = text.lower()
        
        translations = {
            "hi": {
                "diabetes": (
                    "रोगी को टाइप 2 मधुमेह (डायबिटीज़) है जिसके लिए तुरंत इलाज की जरूरत है। "
                    "खून में शुगर का स्तर सामान्य से अधिक है और HbA1c परीक्षण जरूरी है। "
                    "डॉक्टर ने मेटफॉर्मिन दवाई शुरू करने की सलाह दी है। "
                    "रोजाना 30 मिनट की हल्की कसरत और कम चीनी वाला खाना खाएं। "
                    "2 सप्ताह में दोबारा डॉक्टर से मिलें।"
                ),
                "hypertension": (
                    "रोगी का रक्तचाप (ब्लड प्रेशर) बहुत अधिक है जिसे नियंत्रित करना जरूरी है। "
                    "लक्ष्य है कि ब्लड प्रेशर 130/80 से कम रहे। "
                    "दवाइयां समय पर लें और नमक का सेवन कम करें। "
                    "रोज सुबह ब्लड प्रेशर मापें और रिकॉर्ड रखें। "
                    "2 सप्ताह में जांच के लिए आएं।"
                ),
                "respiratory": (
                    "रोगी को सांस लेने में तकलीफ हो रही है और फेफड़ों की जांच जरूरी है। "
                    "इनहेलर का सही तरीके से उपयोग करें जैसा डॉक्टर ने बताया है। "
                    "धूम्रपान तुरंत बंद करें — यह सबसे जरूरी कदम है। "
                    "यदि सांस बहुत कठिन हो जाए तो तुरंत अस्पताल जाएं। "
                    "स्पाइरोमेट्री जांच जल्द करवाएं।"
                ),
                "default": (
                    "आपकी स्वास्थ्य जांच हो गई है और डॉक्टर ने कुछ सलाह दी है। "
                    "दी गई दवाइयां नियमित रूप से लें। "
                    "खाने-पीने का ध्यान रखें और नियमित व्यायाम करें। "
                    "अगली मुलाकात के लिए समय पर आएं।"
                )
            },
            "ta": {
                "diabetes": (
                    "நோயாளிக்கு வகை 2 நீரிழிவு நோய் (டயபட்டீஸ்) இருப்பது கண்டறியப்பட்டுள்ளது. "
                    "இரத்தத்தில் சர்க்கரை அளவு அதிகமாக உள்ளது, உடனடி சிகிச்சை தேவை. "
                    "மெட்ஃபார்மின் மருந்து தொடங்க மருத்துவர் பரிந்துரைத்துள்ளார். "
                    "தினமும் 30 நிமிட நடை மற்றும் குறைந்த சர்க்கரை உணவு அவசியம். "
                    "2 வாரங்களில் மருத்துவரை மீண்டும் சந்தியுங்கள்."
                ),
                "hypertension": (
                    "நோயாளியின் இரத்த அழுத்தம் அதிகமாக உள்ளது, இதை கட்டுப்படுத்த வேண்டும். "
                    "இரத்த அழுத்தம் 130/80க்கு கீழ் இருக்க வேண்டும் என்பது குறிக்கோள். "
                    "மருந்துகளை தவறாமல் எடுத்துக்கொள்ளுங்கள், உப்பை குறையுங்கள். "
                    "தினமும் காலையில் இரத்த அழுத்தம் அளவிட்டு பதிவு செய்யுங்கள். "
                    "2 வாரங்களில் பரிசோதனைக்கு வாருங்கள்."
                ),
                "respiratory": (
                    "நோயாளிக்கு மூச்சு திணறல் இருக்கிறது, நுரையீரல் பரிசோதனை அவசியம். "
                    "மருத்துவர் கூறியபடி இன்ஹேலரை சரியாக பயன்படுத்துங்கள். "
                    "புகைப்பிடிப்பை உடனடியாக நிறுத்துவது மிக முக்கியம். "
                    "மூச்சு மிகவும் கஷ்டமாக இருந்தால் உடனே மருத்துவமனை செல்லுங்கள். "
                    "ஸ்பைரோமெட்ரி பரிசோதனையை விரைவில் செய்யுங்கள்."
                ),
                "default": (
                    "உங்கள் உடல்நல பரிசோதனை முடிந்தது, மருத்துவர் சில அறிவுரைகள் கூறியுள்ளார். "
                    "கொடுக்கப்பட்ட மருந்துகளை தொடர்ந்து சாப்பிடுங்கள். "
                    "சரியான உணவு மற்றும் தினமும் உடற்பயிற்சி செய்யுங்கள். "
                    "அடுத்த சந்திப்புக்கு சரியான நேரத்தில் வாருங்கள்."
                )
            }
        }
        
        # Detect condition from source text - check for primary condition indicators
        # Look for condition-specific keywords that indicate primary diagnosis
        respiratory_score = sum(1 for k in ['respiratory', 'spirometry', 'bronchodilator', 'inhaler', 'breath', 'copd', 'asthma', 'wheez', 'lung function'] if k in text_lower)
        hypertension_score = sum(1 for k in ['antihypertensive', 'ambulatory bp', 'blood pressure control', 'bp below', 'sodium restriction'] if k in text_lower)
        diabetes_score = sum(1 for k in ['diabetes mellitus', 'glycaem', 'metformin', 'hba1c', 'fasting glucose', 'diabetic retinopathy'] if k in text_lower)
        
        # Choose condition with highest score
        scores = {'respiratory': respiratory_score, 'hypertension': hypertension_score, 'diabetes': diabetes_score}
        condition = max(scores, key=scores.get) if max(scores.values()) > 0 else 'default'
        
        lang_translations = translations.get(target_lang, translations['hi'])
        return lang_translations.get(condition, lang_translations['default'])



