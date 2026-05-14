# analyzer/trainer.py
import os
import re
import random
import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# =============== STEP 1: Generate Realistic Synthetic Training Data ===============
def generate_training_data(n_samples=500):
    """
    Generate synthetic resume-JD pairs with realistic match scores.
    In production, replace with real labeled data from HR/analytics team.
    """
    skills_pool = [
        'python', 'django', 'flask', 'react', 'nodejs', 'aws', 'docker', 
        'kubernetes', 'sql', 'mongodb', 'machine learning', 'nlp', 'tensorflow',
        'pytorch', 'scikit-learn', 'pandas', 'numpy', 'git', 'ci/cd', 'agile'
    ]
    
    experience_phrases = [
        'years of experience', 'senior developer', 'led team', 'architected',
        'delivered', 'optimized', 'implemented', 'designed', 'managed'
    ]
    
    data = []
    for _ in range(n_samples):
        # Randomly select JD skills (3-8 skills)
        jd_skills = random.sample(skills_pool, random.randint(3, 8))
        jd_text = f"Looking for developer with {', '.join(jd_skills)} experience."
        
        # Generate resume: match 0-100% of JD skills
        match_ratio = random.random()
        matched_skills = random.sample(jd_skills, int(len(jd_skills) * match_ratio))
        extra_skills = random.sample([s for s in skills_pool if s not in jd_skills], 
                                    random.randint(0, 4))
        resume_skills = matched_skills + extra_skills
        
        # Add experience signals
        exp_bonus = random.random() * 20 if random.random() > 0.3 else 0
        
        # Calculate base score + noise
        base_score = match_ratio * 70 + exp_bonus
        noise = np.random.normal(0, 8)  # Realistic human labeling variance
        final_score = np.clip(base_score + noise, 10, 95)
        
        resume_text = f"Developer skilled in {', '.join(resume_skills)}. "
        if random.random() > 0.5:
            resume_text += f" {random.choice(experience_phrases)} in projects."
        
        data.append({
            'resume_text': resume_text,
            'jd_text': jd_text,
            'match_score': round(final_score, 1),
            'jd_skills': jd_skills,
            'resume_skills': resume_skills,
            'is_good_match': int(final_score >= 60)  # Binary label for classification tasks
        })
    
    return pd.DataFrame(data)


# =============== STEP 2: Feature Engineering ===============
def extract_features(df):
    """
    Create ML-ready features from text data.
    This is where domain knowledge meets ML.
    """
    df = df.copy()
    
    # 1. Text similarity features
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=500)
    tfidf_matrix = vectorizer.fit_transform(df['resume_text'] + ' ' + df['jd_text'])
    
    # Cosine similarity for each pair (approximate)
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = []
    for i in range(len(df)):
        resume_vec = vectorizer.transform([df.iloc[i]['resume_text']])
        jd_vec = vectorizer.transform([df.iloc[i]['jd_text']])
        similarities.append(cosine_similarity(resume_vec, jd_vec)[0][0])
    
    df['tfidf_similarity'] = similarities
    
    # 2. Keyword overlap features
    df['skill_overlap_ratio'] = df.apply(
        lambda row: len(set(row['resume_skills']) & set(row['jd_skills'])) / max(len(row['jd_skills']), 1), 
        axis=1
    )
    
    df['extra_skills_count'] = df.apply(
        lambda row: len(set(row['resume_skills']) - set(row['jd_skills'])), 
        axis=1
    )
    
    # 3. Experience signal (simple heuristic)
    df['experience_score'] = df['resume_text'].str.count(
        r'(years|senior|led|architected|delivered|optimized)', 
        flags=re.IGNORECASE
    ) * 5
    
    # 4. Text length features (proxy for detail/completeness)
    df['resume_length'] = df['resume_text'].str.len()
    df['jd_length'] = df['jd_text'].str.len()
    
    return df


# =============== STEP 3: Train & Evaluate Model ===============
def train_model(df, save_path=None):
    """
    Train RandomForestRegressor with proper ML workflow.
    Returns trained pipeline and evaluation metrics.
    """
    print("🔧 Preparing features...")
    df_featured = extract_features(df)
    
    # Feature columns for model
    feature_cols = [
        'tfidf_similarity', 'skill_overlap_ratio', 'extra_skills_count',
        'experience_score', 'resume_length', 'jd_length'
    ]
    
    X = df_featured[feature_cols]
    y = df_featured['match_score']
    
    # Train/test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=pd.cut(y, bins=5, labels=False)
    )
    
    print("🤖 Training RandomForestRegressor...")
    # Pipeline: scaling + model (good practice even for tree models)
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('regressor', RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        ))
    ])
    
    # Train
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    y_pred = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    # Cross-validation for robustness estimate
    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='neg_mean_absolute_error')
    cv_mae = -cv_scores.mean()
    
    print(f"\n📊 Evaluation Results:")
    print(f"   Test MAE: {mae:.2f} points")
    print(f"   Test R²: {r2:.3f}")
    print(f"   CV MAE (5-fold): {cv_mae:.2f} points")
    print(f"   Feature importances: {dict(zip(feature_cols, pipeline.named_steps['regressor'].feature_importances_))}")
    
    # Save model
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        model_data = {
            'pipeline': pipeline,
            'feature_cols': feature_cols,
            'vectorizer': None,  # Not used in inference for simplicity
            'metrics': {'mae': mae, 'r2': r2, 'cv_mae': cv_mae},
            'feature_importances': dict(zip(feature_cols, pipeline.named_steps['regressor'].feature_importances_))
        }
        joblib.dump(model_data, save_path)
        print(f"💾 Model saved to {save_path}")
    
    return pipeline, {'mae': mae, 'r2': r2, 'cv_mae': cv_mae}


# =============== STEP 4: CLI Entry Point ===============
if __name__ == "__main__":
    print("🚀 Starting ATS ML Training Pipeline")
    print("=" * 50)
    
    # Generate data
    print("📦 Generating synthetic training data...")
    df = generate_training_data(n_samples=500)
    
    # Train
    model_path = os.path.join(os.path.dirname(__file__), "ml_models", "ats_regressor_v1.pkl")
    pipeline, metrics = train_model(df, save_path=model_path)
    
    print("\n✅ Training complete!")
    print(f"📈 Model ready for inference. Test R²: {metrics['r2']:.3f}")