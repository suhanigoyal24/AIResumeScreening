import re
from collections import Counter
from typing import List, Set

from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class ScorerOutput(BaseModel):
    match_score: float = Field(..., description="Calibrated semantic match percentage (0-100)")
    matched_keywords: List[str] = Field(..., description="Skills found in both resume and JD")
    missing_keywords: List[str] = Field(default_factory=list, description="Skills in JD but not in resume")
    semantic_similarity: float = Field(..., description="Raw vector-space contextual score")


# Curated skill vocabulary — extend this list as needed. Add multi-word
# skills too ("machine learning", "ci/cd") since we do substring matching,
# not just single-token overlap.
SKILL_TAXONOMY: Set[str] = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "r",
    # Web / backend frameworks
    "django", "flask", "fastapi", "react", "node", "node.js", "express", "next.js", "vue", "angular",
    "django rest framework", "drf",
    # Data / ML
    "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "scikit-learn",
    "sklearn", "pandas", "numpy", "keras", "opencv", "sbert", "sentence transformers",
    "llm", "rag", "langchain", "faiss",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "sqlite",
    # DevOps / infra
    "docker", "kubernetes", "ci/cd", "jenkins", "git", "github actions", "aws", "gcp",
    "azure", "linux", "nginx", "terraform",
    # APIs / protocols
    "rest api", "graphql", "grpc", "websocket",
}


class ATSScorer:
    """
    Production-grade hybrid ATS Scorer.
    Combines SBERT vector embeddings for contextual semantic analysis with
    a curated skill taxonomy for explicit, human-readable skill matching
    (instead of raw word-frequency overlap, which leaks generic verbs).
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
        text = re.sub(r'[^a-z0-9\s#\+\.\/]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def calculate_metrics(self, resume_text: str, jd_text: str) -> ScorerOutput:
        if not resume_text.strip() or not jd_text.strip():
            return ScorerOutput(match_score=0.0, matched_keywords=[], missing_keywords=[], semantic_similarity=0.0)

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

        matched_terms, missing_terms = self._extract_skill_vocabulary(resume_clean, jd_clean)

        # Blended score: 70% semantic + 30% keyword
        raw_blend = (sbert_sim * 0.7) + (tfidf_sim * 0.3)

        min_expected_blend = 0.05
        max_expected_blend = 0.65
        scaled_score = ((raw_blend - min_expected_blend) / (max_expected_blend - min_expected_blend)) * 100
        final_score = max(20.0, min(98.0, scaled_score))

        print(f"[SCORER] SBERT={sbert_sim:.3f} | TF-IDF={tfidf_sim:.3f} | blend={raw_blend:.3f} | final={final_score:.1f}")

        return ScorerOutput(
            match_score=round(final_score, 1),
            matched_keywords=matched_terms,
            missing_keywords=missing_terms,
            semantic_similarity=round(sbert_sim, 3)
        )

    def _extract_skill_vocabulary(self, resume_clean: str, jd_clean: str):
        """
        Matches against a curated skill taxonomy instead of raw word overlap.
        This is what stops generic verbs ('optimize', 'participate', 'manage',
        etc.) from ever appearing as a "skill" — they simply aren't in
        SKILL_TAXONOMY, so they can't match or be flagged as missing.
        """
        jd_skills_found = {skill for skill in SKILL_TAXONOMY if skill in jd_clean}

        matched = sorted(
            [skill for skill in jd_skills_found if skill in resume_clean]
        )
        missing = sorted(
            [skill for skill in jd_skills_found if skill not in resume_clean]
        )

        return matched, missing