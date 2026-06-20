import re
from ..ats_scorer import ATSScorer

class ATSMLPredictor:
    def __init__(self, model_path=None):
        print('?? Initializing SentenceTransformer Framework Model...')
        self.engine = ATSScorer()
    def predict(self, resume_text, jd_text):
        metrics = self.engine.calculate_metrics(resume_text, jd_text)
        return {
            'score': metrics.match_score,
            'matched_keywords': metrics.matched_keywords,
            'feature_contributions': {'similarity': metrics.semantic_similarity},
            'model_version': 'v2_sbert',
            'confidence': 'high'
        }
