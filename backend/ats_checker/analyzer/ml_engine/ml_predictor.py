# analyzer/ml_engine/ml_predictor.py
import os
import re
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ATSMLPredictor:
    """
    Loads trained ML model and predicts match scores.
    Handles both old (direct model) and new (dict with 'pipeline') formats.
    """
    
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "ats_model.pkl")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ML model not found at {model_path}. Run trainer.py first.")
        
        print(f"🔌 Loading ML model from {model_path}")
        
        # Load the model file
        model_data = joblib.load(model_path)
        
        # Handle both old and new formats
        if isinstance(model_data, dict) and 'pipeline' in model_data:
            # ✅ New format: dict with 'pipeline' key
            self.pipeline = model_data['pipeline']
            self.feature_cols = model_data.get('feature_cols', [
                'tfidf_similarity', 'skill_overlap_ratio', 'extra_skills_count',
                'experience_score', 'resume_length', 'jd_length'
            ])
        else:
            # ⚠️ Old format: direct vectorizer or model
            # Fallback to simple TF-IDF + cosine similarity
            print("⚠️ Old model format detected. Using fallback TF-IDF scorer.")
            self.pipeline = None  # Signal to use fallback
            self.vectorizer = model_data if hasattr(model_data, 'transform') else None
            self.feature_cols = []
        
        print("✅ ML Predictor ready")
    
    def _extract_features_single(self, resume_text: str, jd_text: str) -> dict:
        """Extract features for a single prediction"""
        features = {}
        
        # TF-IDF similarity
        temp_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=500)
        temp_matrix = temp_vectorizer.fit_transform([resume_text, jd_text])
        features['tfidf_similarity'] = cosine_similarity(
            temp_matrix[0:1], temp_matrix[1:2]
        )[0][0]
        
        # Keyword overlap
        def extract_skills(text):
            skill_keywords = [
                'python', 'django', 'flask', 'react', 'nodejs', 'aws', 'docker',
                'kubernetes', 'sql', 'mongodb', 'machine learning', 'nlp', 'tensorflow',
                'pytorch', 'scikit-learn', 'pandas', 'numpy', 'git', 'ci/cd', 'agile'
            ]
            text_lower = text.lower()
            return [s for s in skill_keywords if s in text_lower]
        
        resume_skills = set(extract_skills(resume_text))
        jd_skills = set(extract_skills(jd_text))
        
        features['skill_overlap_ratio'] = (
            len(resume_skills & jd_skills) / max(len(jd_skills), 1)
        )
        features['extra_skills_count'] = len(resume_skills - jd_skills)
        
        # Experience signal
        features['experience_score'] = len(re.findall(
            r'(years|senior|led|architected|delivered|optimized)', 
            resume_text, re.IGNORECASE
        )) * 5
        
        # Length features
        features['resume_length'] = len(resume_text)
        features['jd_length'] = len(jd_text)
        
        return features
    
    def _fallback_predict(self, resume_text: str, jd_text: str) -> dict:
        """Fallback prediction using simple TF-IDF + cosine similarity"""
        # Clean texts
        def clean(t):
            return re.sub(r'[^a-z0-9\s]', ' ', t.lower()).strip()
        
        resume_clean = clean(resume_text)
        jd_clean = clean(jd_text)
        
        # TF-IDF + cosine similarity
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=500)
        tfidf_matrix = vectorizer.fit_transform([jd_clean, resume_clean])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Simple calibration
        import math
        raw = similarity * 100
        calibrated = 100 / (1 + math.exp(-0.1 * (raw - 50)))
        score = max(30, min(90, calibrated))
        
        # Extract matched keywords
        def extract_skills(text):
            skill_keywords = [
                'python', 'django', 'flask', 'react', 'nodejs', 'aws', 'docker',
                'kubernetes', 'sql', 'mongodb', 'machine learning', 'nlp', 'tensorflow',
                'pytorch', 'scikit-learn', 'pandas', 'numpy', 'git', 'ci/cd', 'agile'
            ]
            text_lower = text.lower()
            return [s for s in skill_keywords if s in text_lower]
        
        resume_skills = set(extract_skills(resume_text))
        jd_skills = set(extract_skills(jd_text))
        matched = list(resume_skills & jd_skills)
        
        return {
            'score': round(float(score), 1),
            'matched_keywords': matched[:10],
            'feature_contributions': {'similarity': similarity},
            'model_version': 'fallback_tfidf',
            'confidence': 'medium'
        }
    
    def predict(self, resume_text: str, jd_text: str) -> dict:
        """Predict match score for a resume-JD pair"""
        # Use fallback if pipeline not available
        if self.pipeline is None:
            return self._fallback_predict(resume_text, jd_text)
        
        # Normal prediction with trained pipeline
        features = self._extract_features_single(resume_text, jd_text)
        X = np.array([[features[col] for col in self.feature_cols]])
        
        score = self.pipeline.predict(X)[0]
        score = np.clip(score, 15, 95)
        
        # Extract matched keywords
        def extract_skills(text):
            skill_keywords = [
                'python', 'django', 'flask', 'react', 'nodejs', 'aws', 'docker',
                'kubernetes', 'sql', 'mongodb', 'machine learning', 'nlp', 'tensorflow',
                'pytorch', 'scikit-learn', 'pandas', 'numpy', 'git', 'ci/cd', 'agile'
            ]
            text_lower = text.lower()
            return [s for s in skill_keywords if s in text_lower]
        
        resume_skills = set(extract_skills(resume_text))
        jd_skills = set(extract_skills(jd_text))
        matched = list(resume_skills & jd_skills)
        
        return {
            'score': round(float(score), 1),
            'matched_keywords': matched[:10],
            'feature_contributions': {
                'similarity': features['tfidf_similarity'],
                'skill_match': features['skill_overlap_ratio'],
                'experience': features['experience_score']
            },
            'model_version': 'v1',
            'confidence': 'high' if score >= 70 else 'medium' if score >= 45 else 'low'
        }