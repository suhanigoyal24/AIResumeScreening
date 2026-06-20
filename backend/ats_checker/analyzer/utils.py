import re
import os
import string
import pdfplumber
import docx

SKILL_KEYWORDS = {'python', 'javascript', 'typescript', 'react', 'django', 'flask', 'fastapi', 'sql', 'postgresql', 'mongodb', 'aws', 'docker', 'kubernetes', 'git', 'ci/cd'}

def extract_text_from_file(file_path, file_type):
    try:
        if file_type == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join(page.extract_text() or '' for page in pdf.pages)
        elif file_type in ['docx', 'doc']:
            doc = docx.Document(file_path)
            return '\n'.join(para.text for para in doc.paragraphs)
        return ''
    except Exception as e:
        return ''

def clean_text(text):
    if not text: return ''
    text = text.lower()
    return re.sub(r'[^\w\s]', ' ', text).strip()

def extract_skills(text):
    if not text: return []
    t = text.lower()
    return sorted(list({s for s in SKILL_KEYWORDS if s in t}))

def calculate_weighted_score(*args, **kwargs):
    return {'score': 50.0, 'matched_skills': [], 'missing_skills': []}

nlp = None
STOPWORDS = set()
__all__ = ['nlp', 'STOPWORDS', 'SKILL_KEYWORDS', 'extract_text_from_file', 'clean_text', 'extract_skills', 'calculate_weighted_score']
