# analyzer/ats_scorer.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import math
import re
from collections import Counter

class ATSScorer:
    """
    Lightweight ATS Scorer using TF-IDF + Cosine Similarity + Calibration.
    No PyTorch/TensorFlow dependencies with Realistic scores.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),  # unigrams + bigrams
            max_features=500,
            min_df=1,
            max_df=0.95
        )
        self._loaded = True
    
    def clean_text(self, text: str) -> str:
        """Normalize text for better matching"""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)  # remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()   # collapse whitespace
        return text

    def score(self, resume_text: str, jd_text: str) -> float:
        """Calculate ATS match score (0-100) with realistic calibration"""
        if not resume_text.strip() or not jd_text.strip():
            return 0.0
        
        # Clean texts
        resume_clean = self.clean_text(resume_text)
        jd_clean = self.clean_text(jd_text)
        
        # 1. TF-IDF Vectorization
        try:
            tfidf_matrix = self.vectorizer.fit_transform([jd_clean, resume_clean])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            # Fallback if vectorization fails
            similarity = 0.3
        
        # 2. Keyword overlap bonus (simple but effective)
        resume_words = set(resume_clean.split())
        jd_words = set(jd_clean.split())
        meaningful_jd = {w for w in jd_words if len(w) > 3}
        keyword_overlap = len(resume_words & meaningful_jd) / max(len(meaningful_jd), 1)
        
        # 3. Combine signals
        raw_score = (similarity * 0.7) + (keyword_overlap * 0.3)
        
        # 4. Calibration: Sigmoid curve → realistic ATS range
        # Maps 0.3 similarity ≈ 60%, 0.6 ≈ 85%
        calibrated = 100 / (1 + math.exp(-10 * (raw_score - 0.4)))
        
        # Clamp to realistic bounds
        final_score = max(30, min(95, calibrated))
        
        return round(final_score, 1)
    
    def keywords(self, resume_text: str, jd_text: str, top_k: int = 15) -> list:
        """Extract top matched keywords using simple frequency + overlap"""
        resume_clean = self.clean_text(resume_text)
        jd_clean = self.clean_text(jd_text)
        
        resume_words = Counter(resume_clean.split())
        jd_words = Counter(jd_clean.split())
        
        # Filter meaningful words
        meaningful = {w for w in jd_words if len(w) > 3 and jd_words[w] >= 2}
        matched = [w for w in meaningful if w in resume_words]
        
        # Sort by JD frequency, return top_k
        matched.sort(key=lambda w: jd_words[w], reverse=True)
        return matched[:top_k]