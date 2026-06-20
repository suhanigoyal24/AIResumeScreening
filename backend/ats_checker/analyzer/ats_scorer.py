import re
import math
from collections import Counter
from typing import List
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Enforce clean typing boundaries for your Django views.py
class ScorerOutput(BaseModel):
    match_score: float = Field(..., description="Calibrated semantic match percentage (0-100)")
    matched_keywords: List[str] = Field(..., description="Top domain-specific terms found in both profiles")
    semantic_similarity: float = Field(..., description="Raw vector-space contextual score")

class ATSScorer:
    """
    Production-grade hybrid ATS Scorer.
    Combines SBERT vector embeddings for contextual semantic analysis with 
    TfidfVectorizer token tracking for explicit compliance verification.
    """
    
    def __init__(self):
        # Lightweight ~90MB footprint. Optimized for fast inference on CPU-only containers.
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=500
        )
        self._loaded = True
    
    def clean_text(self, text: str) -> str:
        """Normalize structure and strip syntax noise from raw documents."""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s#\+\.]', ' ', text)  # Keep chars like C++, C#, .NET
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def calculate_metrics(self, resume_text: str, jd_text: str) -> ScorerOutput:
        """
        Executes a dual-signal assessment routing to evaluate candidate fitness.
        Calculates a contextual score via dense vector mappings and cross-verifies keyword presence.
        """
        if not resume_text.strip() or not jd_text.strip():
            return ScorerOutput(match_score=0.0, matched_keywords=[], semantic_similarity=0.0)
        
        resume_clean = self.clean_text(resume_text)
        jd_clean = self.clean_text(jd_text)
        
        # Signal 1: Contextual Semantic Mapping (SBERT)
        # Translates unstructured prose into structural 384-dimensional dense vectors
        embeddings = self.encoder.encode([jd_clean, resume_clean], convert_to_numpy=True)
        sbert_sim = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        
        # Signal 2: Deterministic Compliance Audit (TF-IDF)
        try:
            tfidf_matrix = self.vectorizer.fit_transform([jd_clean, resume_clean])
            tfidf_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception:
            tfidf_sim = sbert_sim  # Fallback to semantic layer if sparse matrix generation collapses
            
        # Extract meaningful intersection keywords
        matched_terms = self._extract_matched_vocabulary(resume_clean, jd_clean)
        
        # Blended Scoring Strategy: 70% Semantic context + 30% Hard keyword compliance
        raw_blend = (sbert_sim * 0.7) + (tfidf_sim * 0.3)
        
        # Sigmoid Calibration Function to map mathematical values into a normalized business scale
        calibrated_score = 100 / (1 + math.exp(-12 * (raw_blend - 0.38)))
        final_score = max(15.0, min(98.5, calibrated_score))
        
        return ScorerOutput(
            match_score=round(final_score, 1),
            matched_keywords=matched_terms[:12],
            semantic_similarity=round(sbert_sim, 3)
        )
        
    def _extract_matched_vocabulary(self, resume_clean: str, jd_clean: str) -> List[str]:
        """Isolates high-frequency technical indicators intersecting both fields."""
        resume_words = Counter(resume_clean.split())
        jd_words = Counter(jd_clean.split())
        
        # Filter core semantic elements (token length > 2 to retain languages like Go, C, R)
        meaningful_tokens = {word for word in jd_words if len(word) >= 2 and jd_words[word] >= 1}
        intersected = [word for word in meaningful_tokens if word in resume_words]
        
        # Sort tokens based on relative contextual density within the target profile
        intersected.sort(key=lambda word: jd_words[word], reverse=True)
        return intersected
