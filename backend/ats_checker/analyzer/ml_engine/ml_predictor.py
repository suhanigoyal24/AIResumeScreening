import re
from typing import Dict, Any
import os, sys

# Robust import: works whether called from ml_engine/ or analyzer/
try:
    from .ats_scorer import ATSScorer
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from analyzer.ml_engine.ats_scorer import ATSScorer


class ATSMLPredictor:
    """
    ML inference wrapper around ATSScorer (SBERT + TF-IDF hybrid).
    Replaces RandomForest pkl — no model file needed.
    """

    def __init__(self, model_path: str = None):
        # model_path ignored — kept for API compatibility with views.py
        print("[ML] Loading SBERT encoder (all-MiniLM-L6-v2)...")
        try:
            self.engine = ATSScorer()
            self._ready = True
            print("[ML] ATSMLPredictor ready: SBERT + TF-IDF hybrid initialized.")
        except Exception as e:
            self._ready = False
            print(f"[ML] ATSScorer init failed: {e}")
            raise

    def predict(self, resume_text: str, jd_text: str) -> Dict[str, Any]:
        """
        Main inference method called by views.py upload_resume().

        Returns dict with keys views.py expects:
          - score (float 0-100)
          - matched_keywords (list[str])
        """
        if not self._ready:
            raise RuntimeError("ATSMLPredictor not initialized.")

        if not resume_text or not resume_text.strip():
            return self._fallback(reason="empty resume text")
        if not jd_text or not jd_text.strip():
            return self._fallback(reason="empty JD text")

        try:
            metrics = self.engine.calculate_metrics(resume_text, jd_text)
        except Exception as e:
            print(f"[ML] calculate_metrics failed: {e}")
            raise

        experience_signals = len(re.findall(
            r'\b(years|senior|led|architected|delivered|optimized|managed|scaled)\b',
            resume_text, re.IGNORECASE
        ))

        # Small experience bonus (max +5) so experienced candidates rank higher
        exp_bonus = min(5.0, experience_signals * 0.8)
        final_score = round(min(95.0, metrics.match_score + exp_bonus), 1)

        return {
            'score': final_score,
            'matched_keywords': metrics.matched_keywords,
            'feature_contributions': {
                'semantic_similarity': metrics.semantic_similarity,
                'tfidf_component': round(1 - metrics.semantic_similarity, 3),
                'experience_bonus': exp_bonus,
                'experience_indicators': experience_signals,
            },
            'model_version': 'v2_sbert_tfidf_hybrid',
            'confidence': (
                'high'   if final_score >= 75 else
                'medium' if final_score >= 50 else
                'low'
            )
        }

    def _fallback(self, reason: str = "") -> Dict[str, Any]:
        print(f"[ML] Fallback triggered: {reason}")
        return {
            'score': 30.0,
            'matched_keywords': [],
            'feature_contributions': {},
            'model_version': 'fallback',
            'confidence': 'low'
        }