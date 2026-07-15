"""
evaluate_ats.py
Golden-set evaluation for ml_engine/ats_scorer.py
One JD, multiple resumes.
Run from: backend/ats_checker/  (so 'analyzer' package resolves)
"""
import os
import sys
import time
from pypdf import PdfReader
from scipy.stats import spearmanr

sys.path.insert(0, os.getcwd())
from analyzer.ml_engine.ats_scorer import ATSScorer

DATA_DIR = r"C:\Users\gsuha\Desktop\eval_data"
JD_FILE = "jd.pdf"
LABEL_MAP = {"good": 3, "moderate": 2, "poor": 1}


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def find_resumes(data_dir):
    files = os.listdir(data_dir)
    return sorted(f for f in files if f.startswith("resume_") and f.endswith(".pdf"))


def main():
    jd_path = os.path.join(DATA_DIR, JD_FILE)
    if not os.path.exists(jd_path):
        print(f"JD file not found: {jd_path}")
        return

    resumes = find_resumes(DATA_DIR)
    if not resumes:
        print(f"No resume_*.pdf files found in {DATA_DIR}")
        return

    print(f"Found {len(resumes)} resumes to score against 1 JD.\n")
    jd_text = extract_text(jd_path)
    scorer = ATSScorer()

    model_scores = []
    human_labels = []
    latencies = []

    for resume_file in resumes:
        resume_path = os.path.join(DATA_DIR, resume_file)
        resume_text = extract_text(resume_path)

        start = time.perf_counter()
        result = scorer.calculate_metrics(resume_text, jd_text)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        print(f"\n--- {resume_file} ---")
        print(f"Model score: {result.match_score}  (SBERT sim: {result.semantic_similarity})")
        print(f"Matched keywords: {result.matched_keywords[:8]}")

        while True:
            label = input("Your honest judgment (good/moderate/poor): ").strip().lower()
            if label in LABEL_MAP:
                break
            print("Please type: good, moderate, or poor")

        model_scores.append(result.match_score)
        human_labels.append(LABEL_MAP[label])

    avg_latency = sum(latencies) / len(latencies)

    print("\n================ RESULTS ================")
    print(f"Resumes evaluated: {len(resumes)}")
    print(f"Average scoring latency: {avg_latency*1000:.1f} ms per resume-JD pair")

    if len(resumes) >= 3:
        correlation, p_value = spearmanr(model_scores, human_labels)
        print(f"Spearman correlation (model vs human judgment): {correlation:.3f}")
        print(f"P-value: {p_value:.4f}")
    else:
        print("Note: Spearman correlation needs at least 3 pairs to be meaningful — skipped.")
    print("===========================================")


if __name__ == "__main__":
    main()
