🤖 AI-Based Resume Screening & Job Description Matching System

Major Project | Department of Computer Science & Applications (CSA)
ITM University | Submitted to Dr. Keerti Shrivastava, Assistant Professor

---

📌 Project Overview

Recruitment teams receive hundreds of resumes per job posting making manual screening
slow, inconsistent and prone to bias. This system uses AI/ML to automate resume parsing,
skill extraction, and candidate ranking.

HR teams can upload up to 20 resumes at once, match them against a job description,
and receive ranked results , cutting screening time by ~70% while improving accuracy
and consistency.

---

❗ Problem Statement

HR teams struggle to efficiently process large volumes of resumes in varied formats
(PDF, DOCX, TXT), leading to:
- Delayed hiring pipelines
- Inconsistent manual evaluation
- Potential loss of qualified candidates

---

✅ Solution

An automated Django-based system that:
- Parses resumes across multiple formats (PDF, DOCX, TXT)
- Extracts skills, experience, and education accurately using NLP
- Ranks candidates using a **hybrid SBERT + TF-IDF scoring model**
- Stores data securely in SQL with a full audit trail
- Delivers explainable, transparent results to HR teams

---

🎯 Objectives

- Accept resume files in multiple formats (PDF, DOCX, TXT)
- Automatically extract text, skills, experience, and education
- Rank candidates based on job description matching using NLP & ML
- Store processed data securely for future reference and audit
- Provide a clean HR interface to upload job descriptions and view ranked results

---

🚀 Features

- 📂 Bulk resume upload — up to **20 resumes at once**
- 📄 Multi-format support — PDF, DOCX, TXT
- 🧠 AI/NLP-based resume parsing & skill extraction
- 📊 Hybrid **SBERT + TF-IDF** candidate ranking
- 🔍 Job description matching & keyword analysis
- 🗃️ Secure SQL storage with audit trail
- ⚡ Clean, responsive HR dashboard

---

🛠️ Tech Stack

| Layer      | Technologies                              |
|------------|-------------------------------------------|
| Frontend   | React (Vite), Tailwind CSS, TypeScript    |
| Backend    | Python, Django, Django REST Framework     |
| AI / NLP   | SBERT, TF-IDF, spaCy / NLTK               |
| Database   | SQLite (with audit trail)                 |
| API        | REST APIs                                 |

---

📂 Project Structure
MajorProject_AIResumeScreening_SuhaniGoyal/
│
├── frontend/        # React (Vite) frontend
├── backend/         # Django backend
└── README.md

---

⚙️ How to Run
Frontend:
cd frontend
npm install
npm run dev
Runs on: http://localhost:5173

Backend:
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
Runs on: http://127.0.0.1:8000

---

👥 Target Users

This system is built for **HR professionals and recruitment teams** who need to:
- Screen large volumes of applicants quickly
- Fairly and consistently rank candidates
- Match resumes to specific job descriptions at scale

---

🌱 Future Enhancements

-🔗 Integration with job portals (LinkedIn, Naukri)
-📈 Advanced ML-based scoring models
-📥 Resume improvement suggestions & download
-🌐 Cloud deployment (AWS / Render)
-📧 Automated candidate shortlisting emails

---

📚 Academic Submission
Project Type : Major Project
Submitted To : Dr. Keerti Shrivastava, Assistant Professor 
Department : Computer Science & Applications (CSA) 
University : ITM University
Submitted By : Suhani Goyal
