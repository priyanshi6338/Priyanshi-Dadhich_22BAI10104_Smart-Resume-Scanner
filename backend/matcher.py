# matcher.py
import os
import openai
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def tfidf_similarity(a, b):
    try:
        vect = TfidfVectorizer().fit([a, b])
        a_v = vect.transform([a]).toarray()
        b_v = vect.transform([b]).toarray()
        return float(cosine_similarity(a_v, b_v)[0,0])
    except Exception:
        return None

def embeddings_for_text(text, model="text-embedding-3-small"):
    resp = openai.Embedding.create(input=[text], model=model)
    return np.array(resp['data'][0]['embedding'])

def semantic_similarity_by_embeddings(a, b, model="text-embedding-3-small"):
    ea = embeddings_for_text(a, model)
    eb = embeddings_for_text(b, model)
    num = float(np.dot(ea, eb))
    denom = (np.linalg.norm(ea) * np.linalg.norm(eb))
    return num / denom

def build_llm_prompt_resume_match(resume_text, job_description, extracted_skills, top_k_skills=10):
    skills_list_string = ", ".join(extracted_skills) if extracted_skills else "No explicit skills found."
    prompt = f"""You are an expert technical recruiter. Compare the resume below with the job description and provide:
1) A numeric fit score from 1 to 10 (1 = poor fit, 10 = perfect fit).
2) A short justification (3-6 bullet points) mentioning matched skills, missing skills, years of experience relevance and any concerns.
3) List top matched skills from the resume.

Job description:
{job_description}

Resume (extracted text):
{resume_text}

Extracted skills: {skills_list_string}

Please output JSON with keys: score (int), justification (list), matched_skills (list).
"""
    return prompt

def llm_score_resume(resume_text, job_description, extracted_skills, model="gpt-4o-mini", max_tokens=300):
    prompt = build_llm_prompt_resume_match(resume_text, job_description, extracted_skills)
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role":"system","content":"You are a helpful recruiter assistant."},
                  {"role":"user","content":prompt}],
        max_tokens=max_tokens,
        temperature=0.0
    )
    out = resp['choices'][0]['message']['content']
    return out
