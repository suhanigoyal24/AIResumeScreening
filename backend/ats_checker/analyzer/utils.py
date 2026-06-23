import re
import pdfplumber
import docx

# Expanded from 15 → 80+ skills covering web, data, cloud, soft skills
SKILL_KEYWORDS = {
    # Languages
    'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'rust',
    'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',

    # Web frontend
    'react', 'angular', 'vue', 'nextjs', 'html', 'css', 'tailwind', 'redux',
    'webpack', 'vite', 'jquery',

    # Web backend
    'django', 'flask', 'fastapi', 'nodejs', 'express', 'spring', 'rails',
    'graphql', 'rest', 'api',

    # Data / ML / AI
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
    'matplotlib', 'seaborn', 'huggingface', 'openai', 'langchain',
    'data analysis', 'data science', 'statistics',

    # Databases
    'sql', 'postgresql', 'mysql', 'sqlite', 'mongodb', 'redis', 'elasticsearch',
    'cassandra', 'firebase', 'supabase',

    # Cloud / DevOps
    'aws', 'gcp', 'azure', 'docker', 'kubernetes', 'terraform', 'ansible',
    'ci/cd', 'github actions', 'jenkins', 'linux', 'bash',

    # Tools
    'git', 'github', 'jira', 'figma', 'postman', 'vs code',

    # Soft / process
    'agile', 'scrum', 'leadership', 'communication', 'problem solving',
    'teamwork', 'project management',

    # Mobile
    'android', 'ios', 'react native', 'flutter',
}


def extract_text_from_file(file_path, file_type):
    try:
        if file_type == 'pdf':
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join(page.extract_text() or '' for page in pdf.pages)
        elif file_type in ['docx', 'doc']:
            doc = docx.Document(file_path)
            return '\n'.join(para.text for para in doc.paragraphs)
        return ''
    except Exception:
        return ''


def clean_text(text):
    if not text:
        return ''
    text = text.lower()
    return re.sub(r'[^\w\s]', ' ', text).strip()


def extract_skills(text):
    if not text:
        return []
    t = text.lower()
    # Multi-word skills need 'in' check, not just substring
    found = set()
    for skill in SKILL_KEYWORDS:
        if skill in t:
            found.add(skill)
    return sorted(list(found))


def calculate_weighted_score(resume_text, jd_text, resume_skills, job_skills, resume_doc=None, job_doc=None):
    """
    Real skill-overlap scoring to replace the broken stub that returned 50.0 always.
    Used as the 15% traditional blend component in views.py.
    """
    if not job_skills:
        return {'score': 50.0, 'matched_skills': [], 'missing_skills': []}

    matched = list(set(resume_skills) & set(job_skills))
    missing = list(set(job_skills) - set(resume_skills))

    skill_overlap_pct = (len(matched) / len(job_skills)) * 100

    # Bonus: keyword density in resume text vs jd text
    jd_words = set(jd_text.lower().split())
    resume_words = set(resume_text.lower().split())
    word_overlap = len(jd_words & resume_words) / max(len(jd_words), 1)
    word_bonus = min(20, word_overlap * 100)

    score = round(min(95.0, max(10.0, skill_overlap_pct * 0.8 + word_bonus)), 1)

    return {
        'score': score,
        'matched_skills': matched,
        'missing_skills': missing
    }


# spaCy nlp object — set to None since we're using SBERT instead
# views.py uses this for nlp(resume_text) call, so we return a duck-typed stub
class _DocStub:
    """Stub so nlp(text) doesn't crash in views.py when spaCy isn't installed."""
    def __init__(self, text): pass

class _NLPStub:
    def __call__(self, text): return _DocStub(text)

nlp = _NLPStub()
STOPWORDS = set()

__all__ = [
    'nlp', 'STOPWORDS', 'SKILL_KEYWORDS',
    'extract_text_from_file', 'clean_text',
    'extract_skills', 'calculate_weighted_score'
]