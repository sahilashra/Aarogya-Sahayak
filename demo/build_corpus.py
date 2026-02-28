import os
"""
Build FAISS index from synthetic PMC corpus for demo mode.
Run this script once to generate demo/pmc_corpus/faiss_index.index
and demo/pmc_corpus/faiss_index_metadata.pkl
"""
import os
import sys
import pickle
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import faiss
from src.backend.lib.bedrock_client import BedrockClient

CORPUS_DOCUMENTS = [
    {
        "title": "Evidence-Based Management of Type 2 Diabetes Mellitus in Primary Care Settings",
        "pmcid": "PMC8901234",
        "doi": "10.1000/diabetes.2023.001",
        "content": (
            "Type 2 diabetes mellitus management requires individualized glycemic targets. "
            "Metformin remains first-line therapy for most patients with T2DM unless contraindicated. "
            "HbA1c monitoring every 3 months guides treatment intensification. "
            "Lifestyle interventions including diet and exercise reduce cardiovascular risk. "
            "SGLT2 inhibitors and GLP-1 agonists provide cardiovascular and renal protection."
        ),
        "snippet": (
            "Type 2 diabetes mellitus (T2DM) is a chronic metabolic disorder characterized by hyperglycemia "
            "resulting from insulin resistance and progressive beta-cell dysfunction. Management requires a "
            "patient-centered approach with individualized glycemic targets."
        )
    },
    {
        "title": "Hypertension Control Strategies: A Systematic Review of Non-Pharmacological and Pharmacological Interventions",
        "pmcid": "PMC8901235",
        "doi": "10.1000/hypertension.2023.002",
        "content": (
            "Hypertension management combines lifestyle modification with pharmacotherapy. "
            "ACE inhibitors and ARBs are preferred in diabetic patients with hypertension. "
            "Target blood pressure below 130/80 mmHg reduces cardiovascular events. "
            "Regular monitoring and medication adherence are essential for blood pressure control. "
            "Amlodipine and thiazide diuretics are effective first-line agents."
        ),
        "snippet": (
            "Hypertension affects approximately 1.3 billion people worldwide and is a major risk factor for "
            "cardiovascular disease, stroke, and chronic kidney disease. Effective blood pressure control "
            "requires both pharmacological and non-pharmacological strategies."
        )
    },
    {
        "title": "Respiratory Disease Management: COPD, Asthma, and Pneumonia Clinical Guidelines",
        "pmcid": "PMC8901236",
        "doi": "10.1000/respiratory.2023.003",
        "content": (
            "COPD management uses bronchodilators and inhaled corticosteroids to reduce exacerbations. "
            "Asthma step therapy begins with short-acting beta-agonists and escalates with severity. "
            "Spirometry is essential for diagnosis and monitoring of obstructive lung disease. "
            "Smoking cessation is the most effective intervention for COPD progression. "
            "Oxygen therapy is indicated when SpO2 falls below 88 percent."
        ),
        "snippet": (
            "Chronic obstructive pulmonary disease and asthma represent the most common obstructive "
            "respiratory conditions. Evidence-based management reduces hospitalization rates and "
            "improves quality of life through structured pharmacotherapy."
        )
    },
    {
        "title": "Lifestyle Interventions for Prevention and Management of Non-Communicable Diseases",
        "pmcid": "PMC8901237",
        "doi": "10.1000/lifestyle.2023.004",
        "content": (
            "Regular physical activity of 150 minutes per week reduces diabetes and cardiovascular risk. "
            "Mediterranean and low-glycemic-index diets improve metabolic parameters in T2DM. "
            "Weight loss of 5 to 10 percent body weight significantly improves insulin sensitivity. "
            "Smoking cessation reduces cardiovascular mortality by 50 percent within one year. "
            "Stress reduction and sleep hygiene are underutilized components of chronic disease management."
        ),
        "snippet": (
            "Non-communicable diseases including diabetes, hypertension, and cardiovascular disease "
            "share common modifiable risk factors amenable to lifestyle interventions. Evidence demonstrates "
            "significant benefit from structured diet, exercise, and behavioral change programs."
        )
    },
    {
        "title": "Medication Adherence in Chronic Disease Management: Barriers and Interventions",
        "pmcid": "PMC8901238",
        "doi": "10.1000/adherence.2023.005",
        "content": (
            "Medication non-adherence affects 50 percent of patients with chronic conditions. "
            "Simplified dosing regimens and pill organizers improve adherence rates. "
            "Patient education about medication purpose and side effects increases compliance. "
            "Regular follow-up appointments are associated with higher medication adherence. "
            "Fixed-dose combination therapy reduces pill burden and improves outcomes."
        ),
        "snippet": (
            "Medication non-adherence is a major barrier to effective chronic disease management, with "
            "approximately 50 percent of patients not taking medications as prescribed. Structured "
            "interventions including reminders and education improve adherence significantly."
        )
    },
    {
        "title": "Patient Education and Health Literacy in Chronic Disease Self-Management",
        "pmcid": "PMC8901239",
        "doi": "10.1000/education.2023.006",
        "content": (
            "Health literacy strongly predicts self-management behaviors in chronic disease. "
            "Teach-back methods improve patient understanding of discharge instructions. "
            "Visual aids and simplified language enhance comprehension in low-literacy populations. "
            "Peer support programs improve diabetes self-management in South Asian populations. "
            "Digital health tools and mobile apps support remote monitoring and patient engagement."
        ),
        "snippet": (
            "Effective patient education is fundamental to chronic disease self-management, empowering patients "
            "to actively participate in their care and make informed decisions. Health literacy, defined as "
            "the ability to obtain and understand health information, is a key determinant of outcomes."
        )
    }
]

def build_index():
    os.makedirs("demo/pmc_corpus", exist_ok=True)
    client = BedrockClient(aws_mode=os.environ.get("AWS_MODE", "mock"))
    dimension = 1536
    index = faiss.IndexFlatIP(dimension)
    embeddings = []
    for doc in CORPUS_DOCUMENTS:
        emb = client.get_embeddings(doc["content"])
        vec = np.array(emb, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        embeddings.append(vec)
    matrix = np.stack(embeddings).astype(np.float32)
    index.add(matrix)
    faiss.write_index(index, "demo/pmc_corpus/faiss_index.index")
    metadata = [
        {
            "title": d["title"],
            "pmcid": d["pmcid"],
            "doi": d["doi"],
            "content": d["content"],
            "snippet": d["snippet"]
        }
        for d in CORPUS_DOCUMENTS
    ]
    with open("demo/pmc_corpus/faiss_index_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)
    print(f"Built FAISS index with {len(CORPUS_DOCUMENTS)} documents.")
    print("Saved: demo/pmc_corpus/faiss_index.index")
    print("Saved: demo/pmc_corpus/faiss_index_metadata.pkl")

if __name__ == "__main__":
    build_index()

