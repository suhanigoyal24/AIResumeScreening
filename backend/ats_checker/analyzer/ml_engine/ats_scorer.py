import re
import math
from collections import Counter
from typing import List
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


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
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=500
        )
        self._loaded = True

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s#\+\.]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def calculate_metrics(self, resume_text: str, jd_text: str) -> ScorerOutput:
        if not resume_text.strip() or not jd_text.strip():
            return ScorerOutput(match_score=0.0, matched_keywords=[], semantic_similarity=0.0)

        resume_clean = self.clean_text(resume_text)
        jd_clean = self.clean_text(jd_text)

        # Signal 1: SBERT semantic similarity
        embeddings = self.encoder.encode([jd_clean, resume_clean], convert_to_numpy=True)
        sbert_sim = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])

        # Signal 2: TF-IDF keyword similarity
        try:
            tfidf_matrix = self.vectorizer.fit_transform([jd_clean, resume_clean])
            tfidf_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except Exception:
            tfidf_sim = sbert_sim

        matched_terms = self._extract_matched_vocabulary(resume_clean, jd_clean)

        # Blended score: 70% semantic + 30% keyword
        raw_blend = (sbert_sim * 0.7) + (tfidf_sim * 0.3)

        # Linear min-max normalization spreads scores evenly based on real quality.
        min_expected_blend = 0.05
        max_expected_blend = 0.65
        
        # Calculate matching percentage cleanly
        scaled_score = ((raw_blend - min_expected_blend) / (max_expected_blend - min_expected_blend)) * 100
        
        # Clamp bounds logically between 20% and 98%
        final_score = max(20.0, min(98.0, scaled_score))

        print(f"[SCORER] SBERT={sbert_sim:.3f} | TF-IDF={tfidf_sim:.3f} | blend={raw_blend:.3f} | final={final_score:.1f}")

        return ScorerOutput(
            match_score=round(final_score, 1),
            matched_keywords=matched_terms[:12],
            semantic_similarity=round(sbert_sim, 3)
        )

    def _extract_matched_vocabulary(self, resume_clean: str, jd_clean: str) -> List[str]:
        resume_words = Counter(resume_clean.split())
        jd_words = Counter(jd_clean.split())

        meaningful_tokens = {word for word in jd_words if len(word) >= 2 and jd_words[word] >= 1}
        intersected = [word for word in meaningful_tokens if word in resume_words]
        intersected.sort(key=lambda word: jd_words[word], reverse=True)
        return intersected
