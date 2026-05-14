# analyzer/utils.py
import re, os, joblib, spacy, pdfplumber, docx, string
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load spaCy once at module level (global)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Auto-download if not installed: python -m spacy download en_core_web_sm
    raise ImportError("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")

# Download NLTK stopwords once (run once manually if needed)
# import nltk; nltk.download('stopwords')
STOPWORDS = set(stopwords.words("english"))

# Curated skill dictionary (expand as needed)
SKILL_KEYWORDS = {
    'python', 'javascript', 'typescript', 'react', 'django', 'flask', 'fastapi',
    'sql', 'postgresql', 'mongodb', 'machine learning', 'deep learning', 'nlp',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'tensorflow', 'pytorch',
    'git', 'ci/cd', 'agile', 'scrum', 'rest api', 'graphql', 'linux', 'bash'
}

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract raw text from PDF or DOCX files"""
    try:
        if file_type == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages if page.extract_text())
        elif file_type in ['docx', 'doc']:
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
        return ""
    except Exception as e:
        print(f"[ERROR] Text extraction failed for {file_path}: {e}")
        return ""

def clean_text(text: str) -> str:
    """Lowercase, remove punctuation/stopwords, lemmatize"""
    if not text:
        return ""
    doc = nlp(text.lower())
    tokens = [
        token.lemma_.strip() for token in doc 
        if token.is_alpha 
        and token.text not in STOPWORDS 
        and len(token.text) > 2
        and not token.like_url
        and not token.like_email
    ]
    return " ".join(tokens)

def extract_skills(text: str) -> list:
    """Extract skills using keyword matching + basic NER"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = set()
    
    # 1. Keyword matching
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found_skills.add(skill)
    
    # 2. Optional: spaCy NER for organizations/products that might be skills
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["PRODUCT", "ORG"] and 2 <= len(ent.text.split()) <= 4:
            candidate = ent.text.lower().strip()
            # Avoid adding generic terms
            if candidate not in STOPWORDS and candidate not in ['university', 'college', 'company']:
                found_skills.add(candidate)
    
    return sorted(list(found_skills))

def calculate_weighted_score(resume_text: str, job_text: str, resume_skills: list, job_skills: list, resume_doc=None, job_doc=None) -> dict:
    """
    Calculate weighted match score:
    - 40% TF-IDF semantic similarity
    - 30% Skill match (Jaccard index)
    - 20% Experience keyword match
    - 10% Education keyword match
    """
    # Clean texts for vectorization
    clean_resume = clean_text(resume_text)
    clean_job = clean_text(job_text)
    
    # 1. TF-IDF Similarity (40%)
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=500)
        tfidf_matrix = vectorizer.fit_transform([clean_job, clean_resume])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except:
        # Fallback if vectorization fails
        similarity = 0.0
    
    # 2. Skill Match - Jaccard Index (30%)
    resume_set = set(resume_skills)
    job_set = set(job_skills)
    if not job_set and not resume_set:
        skill_match = 1.0  # Both empty = perfect match
    else:
        intersection = resume_set & job_set
        union = resume_set | job_set
        skill_match = len(intersection) / len(union) if union else 0.0
    
    # 3. Experience Score (20%) - keyword heuristic
    exp_keywords = ['year', 'years', 'senior', 'lead', 'manager', 'director', 'experience', 'x+', '+ years']
    resume_exp_count = sum(1 for kw in exp_keywords if kw in resume_text.lower())
    job_exp_count = sum(1 for kw in exp_keywords if kw in job_text.lower())
    exp_score = min(resume_exp_count / max(job_exp_count, 1), 1.0)
    
    # 4. Education Score (10%) - degree keywords
    edu_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'bsc', 'msc', 'mba', 'education']
    resume_edu_count = sum(1 for kw in edu_keywords if kw in resume_text.lower())
    job_edu_count = sum(1 for kw in edu_keywords if kw in job_text.lower())
    if job_edu_count == 0:
        edu_score = 1.0 if resume_edu_count > 0 else 0.5  # Neutral if JD doesn't specify
    else:
        edu_score = min(resume_edu_count / job_edu_count, 1.0)
    
    # Weighted final score (0.0 to 1.0)
    final_score = (
        0.40 * similarity +
        0.30 * skill_match +
        0.20 * exp_score +
        0.10 * edu_score
    )
    
    # Prepare result
    matched_skills = sorted(list(resume_set & job_set))
    missing_skills = sorted(list(job_set - resume_set))
    
    return {
        "score": round(final_score * 100, 2),  # Return as percentage for frontend
        "breakdown": {
            "semantic_similarity": round(similarity * 100, 2),
            "skill_match": round(skill_match * 100, 2),
            "experience_fit": round(exp_score * 100, 2),
            "education_fit": round(edu_score * 100, 2)
        },
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "strengths": _generate_strengths(matched_skills, similarity),
        "weaknesses": _generate_weaknesses(missing_skills, exp_score, edu_score),
        "recommendations": _generate_recommendations(missing_skills, exp_score, edu_score)
    }

def _generate_strengths(matched_skills: list, similarity: float) -> list:
    strengths = []
    if matched_skills:
        top_skills = matched_skills[:3]
        strengths.append(f"✅ Strong alignment in: {', '.join(top_skills)}")
    if similarity > 0.7:
        strengths.append("✅ Resume language closely matches job description")
    return strengths if strengths else ["✅ No major red flags detected"]

def _generate_weaknesses(missing_skills: list, exp_score: float, edu_score: float) -> list:
    weaknesses = []
    if missing_skills:
        weaknesses.append(f"⚠️ Missing key skills: {', '.join(missing_skills[:3])}")
    if exp_score < 0.4:
        weaknesses.append("⚠️ Limited evidence of required experience level")
    if edu_score < 0.4:
        weaknesses.append("⚠️ Education background may not fully align")
    return weaknesses if weaknesses else ["✅ Well-rounded candidate profile"]

def _generate_recommendations(missing_skills: list, exp_score: float, edu_score: float) -> list:
    recs = []
    if missing_skills:
        recs.append(f"💡 Consider highlighting projects using: {', '.join(missing_skills[:2])}")
    if exp_score < 0.5:
        recs.append("💡 Quantify achievements with metrics to demonstrate impact")
    if edu_score < 0.5:
        recs.append("💡 Add relevant certifications or courses to strengthen profile")
    if not recs:
        recs.append("💡 Tailor resume to emphasize matched keywords from job description")
    return recs

# ✅ Explicit exports - prevents circular import issues
__all__ = [
    'nlp',
    'STOPWORDS', 
    'SKILL_KEYWORDS',
    'extract_text_from_file',
    'clean_text',
    'extract_skills', 
    'calculate_weighted_score',
    '_generate_strengths',
    '_generate_weaknesses',
    '_generate_recommendations'
]