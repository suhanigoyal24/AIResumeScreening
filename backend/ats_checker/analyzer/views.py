from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
from django.db.models.functions import TruncDate
import os, re, traceback
from .models import Candidate, JobDescription, MatchScore, MLAnalysis
from .utils import extract_text_from_file, extract_skills, calculate_weighted_score, extract_contact_info, nlp
from django.views.decorators.cache import never_cache
from datetime import timedelta
from collections import Counter

_ats_scorer = None

def get_ml_predictor():
    global _ats_scorer
    if _ats_scorer is None:
        try:
            from .ml_engine.ats_scorer import ATSScorer
            _ats_scorer = ATSScorer()
            print("Hybrid SBERT+TFIDF Scorer loaded successfully")
        except Exception as e:
            print(f"ATSScorer unavailable: {e}")
    return _ats_scorer


def extract_keywords(text, max_keywords=30):
    words = re.findall(r'\b[A-Za-z]{3,20}\b', text.lower())
    stopwords = {
        'the', 'and', 'for', 'with', 'this', 'that', 'you', 'are', 'will', 'can',
        'have', 'has', 'had', 'was', 'were', 'been', 'being', 'is', 'am',
        'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
        'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'our', 'your', 'they', 'them',
        'which', 'who', 'what', 'would', 'could', 'should', 'may', 'might', 'must'
    }
    filtered = [w for w in words if w not in stopwords]
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]


# POST /api/upload/
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_resume(request):
    print(f"[UPLOAD] User: {request.user.username}")
    resumes = request.FILES.getlist('resumes')
    job_description_text = request.data.get('job_description', '').strip()
    jd_file = request.FILES.get('jd_file')
    session_id = request.data.get('session_id', f"session_{timezone.now().timestamp()}")

    if not resumes:
        return Response({"error": "No resume files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
    if not job_description_text and not jd_file:
        return Response({"error": "Missing job description"}, status=status.HTTP_400_BAD_REQUEST)

    jd_temp_path = None
    try:
        if jd_file and not job_description_text:
            jd_ext = os.path.splitext(jd_file.name)[1].lower()
            jd_temp_path = default_storage.save(f"jd_temp/{jd_file.name}", jd_file)
            jd_full_path = os.path.join(settings.MEDIA_ROOT, jd_temp_path)
            job_description_text = extract_text_from_file(jd_full_path, jd_ext[1:])
        if not job_description_text.strip():
            return Response({"error": "Could not extract job description text"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as jd_error:
        traceback.print_exc()
        return Response({"error": "Failed to process job description", "details": str(jd_error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if jd_temp_path and os.path.exists(os.path.join(settings.MEDIA_ROOT, jd_temp_path)):
            try:
                os.remove(os.path.join(settings.MEDIA_ROOT, jd_temp_path))
                default_storage.delete(jd_temp_path)
            except:
                pass

    results = []
    predictor = get_ml_predictor()
    for resume in resumes:
        result = {"filename": resume.name, "success": False}
        try:
            file_ext = os.path.splitext(resume.name)[1].lower()
            if file_ext not in ['.pdf', '.docx', '.doc']:
                result["error"] = f"Unsupported file type: {file_ext}"
                results.append(result)
                continue
            file_path = default_storage.save(f"resumes/{resume.name}", resume)
            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
            resume_text = extract_text_from_file(full_path, file_ext[1:])
            if not resume_text.strip():
                result["error"] = "Could not extract text from resume"
                results.append(result)
                continue

            resume_skills = extract_skills(resume_text)
            job_skills = extract_skills(job_description_text)
            contact_info = extract_contact_info(resume_text)
            resume_keywords = extract_keywords(resume_text)
            job_keywords = extract_keywords(job_description_text)
            matched_keywords = list(set(resume_keywords) & set(job_keywords))
            missing_keywords = list(set(job_keywords) - set(resume_keywords))
            matched_skills = sorted(list(set(resume_skills) & set(job_skills)))
            missing_skills = sorted(list(set(job_skills) - set(resume_skills)))

            resume_doc = nlp(resume_text)
            job_doc = nlp(job_description_text)
            base_result = calculate_weighted_score(
                resume_text, job_description_text,
                resume_skills, job_skills, resume_doc, job_doc
            )

            if predictor:
                try:
                    scorer_result = predictor.calculate_metrics(resume_text, job_description_text)
                    ml_score = scorer_result.match_score
                    final_score = round(ml_score * 0.7 + base_result['score'] * 0.3, 1)
                except Exception as ml_error:
                    print(f"Scorer failed for {resume.name}: {ml_error}")
                    final_score = base_result['score']
            else:
                final_score = base_result['score']

            candidate_name = resume.name.rsplit('.', 1)[0]
            candidate = Candidate.objects.create(
                name=candidate_name,
                email=contact_info["email"],
                phone=contact_info["phone"],
                linkedin_url=contact_info["linkedin_url"],
                resume_file=file_path,
                extracted_text=resume_text[:5000],
                extracted_skills=resume_skills,
                session_id=session_id,
                uploaded_by=request.user
            )
            MatchScore.objects.create(
                candidate=candidate,
                score=final_score / 100,
                missing_skills=missing_skills,
                matched_skills=matched_skills
            )
            result.update({
                "success": True,
                "candidate_id": candidate.id,
                "score": final_score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "contact": {
                    "email": contact_info["email"],
                    "phone": contact_info["phone"],
                    "linkedin_url": contact_info["linkedin_url"]
                }
            })
            print(f"[SUCCESS] {resume.name} - Score: {final_score}")
        except Exception as e:
            print(f"[ERROR] {resume.name}: {e}")
            traceback.print_exc()
            result["error"] = str(e)
        results.append(result)

    return Response({
        "session_id": session_id,
        "results": results
    }, status=status.HTTP_200_OK)


# GET /api/candidates/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def list_candidates(request):
    try:
        candidates = Candidate.objects.filter(uploaded_by=request.user).order_by('-id')
        results = []
        for c in candidates:
            match_score = MatchScore.objects.filter(candidate=c).first()
            score = round((match_score.score * 100) if match_score else 0, 1)

            if score >= 75:
                reason = "Strong match: high skill coverage and keyword alignment."
            elif score >= 60:
                reason = "Good match: meets most core requirements."
            else:
                reason = "Weak match: missing key skills or experience."

            resume_url = ""
            if c.resume_file:
                try:
                    resume_url = request.build_absolute_uri(c.resume_file.url)
                except Exception:
                    pass

            results.append({
                "id": c.id,
                "name": c.name,
                "score": score,
                "status": c.status or "New",
                "remarks": c.remarks or "",
                "resume_url": resume_url,
                "ai_reasoning": reason,
                "matched_skills": match_score.matched_skills if match_score else [],
                "missing_skills": match_score.missing_skills if match_score else [],
                "contact": {
                    "email": c.email or "",
                    "phone": c.phone or "",
                    "linkedin_url": c.linkedin_url or ""
                }
            })
        return Response(results, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Failed to load candidates"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET /api/dashboard-analytics/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    candidates = Candidate.objects.filter(uploaded_by=request.user)
    if not candidates.exists():
        return Response({
            'total_candidates': 0,
            'skills_coverage': {},
            'top_missing_skills': {},
            'score_trend': []
        })

    all_skills = []
    missing_skills = []
    match_scores = MatchScore.objects.filter(candidate__in=candidates)
    for ms in match_scores:
        if ms.matched_skills:
            all_skills.extend(ms.matched_skills)
        if ms.missing_skills:
            missing_skills.extend(ms.missing_skills)

    score_trend_qs = MatchScore.objects.filter(candidate__in=candidates)\
        .annotate(date=TruncDate('candidate__created_at'))\
        .values('date').annotate(avg_score=Avg('score')).order_by('date')

    score_trend = [
        {"date": item['date'].strftime('%Y-%m-%d'), "avg_score": round(item['avg_score'] * 100, 1)}
        for item in score_trend_qs if item['date']
    ]

    return Response({
        'total_candidates': candidates.count(),
        'skills_coverage': dict(Counter(all_skills).most_common(10)),
        'top_missing_skills': dict(Counter(missing_skills).most_common(10)),
        'score_trend': score_trend,
    })


# POST /api/candidates/<id>/update_status/
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_candidate_status(request, candidate_id):
    try:
        candidate = Candidate.objects.get(id=candidate_id, uploaded_by=request.user)
        candidate.status = request.data.get('status', candidate.status)
        candidate.remarks = request.data.get('remarks', candidate.remarks)
        candidate.save()
        return Response({"success": True, "status": candidate.status, "remarks": candidate.remarks})
    except Candidate.DoesNotExist:
        return Response({"error": "Candidate not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# GET /api/dashboard/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def dashboard_data(request):
    min_score = float(request.query_params.get('min_score', 0))
    all_candidates = Candidate.objects.filter(uploaded_by=request.user).order_by('-created_at')
    candidates_list = []
    for cand in all_candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        score = round((match_score.score * 100) if match_score else 0, 1)
        if score >= min_score:
            candidates_list.append({
                "id": cand.id,
                "name": cand.name,
                "score": score,
                "verdict": "Shortlist" if score >= 60 else "Review",
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
                "missing_keywords": (match_score.missing_skills if match_score else [])[:10],
                "contact": {
                    "email": cand.email or "",
                    "phone": cand.phone or "",
                    "linkedin_url": cand.linkedin_url or ""
                }
            })

    total = all_candidates.count()
    avg_score = MatchScore.objects.filter(candidate__uploaded_by=request.user).aggregate(Avg('score'))['score__avg'] or 0
    passed = MatchScore.objects.filter(candidate__uploaded_by=request.user, score__gte=0.6).count()

    return Response({
        "summary": {
            "total_resumes": total,
            "avg_score": round((avg_score or 0) * 100, 1),
            "pass_rate_percent": round((passed / max(total, 1)) * 100, 1),
            "last_updated": timezone.now().isoformat()
        },
        "candidates": candidates_list,
    }, status=status.HTTP_200_OK)


# GET /api/dashboard/latest/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def dashboard_latest(request):
    cutoff = timezone.now() - timedelta(minutes=10)
    recent_candidates = Candidate.objects.filter(
        uploaded_by=request.user, created_at__gte=cutoff
    ).order_by('-created_at')
    if not recent_candidates:
        return Response({"candidates": [], "summary": {"total_candidates": 0, "avg_score": 0}}, status=200)
    candidates_list = []
    for cand in recent_candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
            "verdict": "Shortlist" if (match_score and match_score.score and match_score.score >= 0.6) else "Review",
            "contact": {"email": cand.email or "", "phone": cand.phone or "", "linkedin_url": cand.linkedin_url or ""}
        })
    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    return Response({
        "summary": {
            "total_candidates": len(candidates_list),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        },
        "candidates": candidates_list,
    }, status=200)


# GET /api/dashboard/session/<session_id>/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def dashboard_by_session(request, session_id):
    candidates = Candidate.objects.filter(
        uploaded_by=request.user, session_id=session_id
    ).order_by('-created_at')
    if not candidates:
        return Response({"session_id": session_id, "candidates": [], "summary": {"total": 0}}, status=200)
    candidates_list = []
    for cand in candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
            "verdict": "Shortlist" if (match_score and match_score.score and match_score.score >= 0.6) else "Review",
            "contact": {"email": cand.email or "", "phone": cand.phone or "", "linkedin_url": cand.linkedin_url or ""}
        })
    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    return Response({
        "session_id": session_id,
        "candidates": candidates_list,
        "summary": {
            "total": len(candidates_list),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        }
    }, status=200)


# GET /api/dashboard/history/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@never_cache
def dashboard_history(request):
    try:
        page = int(request.query_params.get('page', 1))
        page_size = 20
        search = request.query_params.get('search', '').lower()
        min_score = float(request.query_params.get('min_score', 0))
        candidates = Candidate.objects.filter(uploaded_by=request.user).order_by('-created_at')
        if search:
            candidates = candidates.filter(name__icontains=search)
        if min_score > 0:
            candidates = candidates.filter(matches__score__gte=min_score / 100).distinct()
        total = candidates.count()
        paginated = candidates[(page - 1) * page_size: page * page_size]
        results = []
        for cand in paginated:
            match_score = cand.matches.first()
            results.append({
                "id": cand.id,
                "name": cand.name,
                "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
                "verdict": "Shortlist" if (match_score and match_score.score and match_score.score >= 0.6) else "Review",
                "status": cand.status or "New",
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "matched_keywords": (match_score.matched_skills if match_score else [])[:15],
                "missing_keywords": (match_score.missing_skills if match_score else [])[:15],
                "contact": {
                    "email": cand.email or "",
                    "phone": cand.phone or "",
                    "linkedin_url": cand.linkedin_url or ""
                }
            })
        return Response({
            "results": results,
            "pagination": {
                "page": page, "page_size": page_size,
                "total": total, "total_pages": (total + page_size - 1) // page_size
            }
        }, status=200)
    except Exception as e:
        print(f"[ERROR in dashboard_history] {e}")
        return Response({"error": "Internal server error", "details": str(e)}, status=500)


# POST /api/ml-analyze/
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ml_analyze(request):
    resume_file = request.FILES.get('resume')
    jd = request.data.get('job_description', '').strip()
    if not resume_file or not jd:
        return Response({"error": "Missing resume file or job_description"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        file_ext = os.path.splitext(resume_file.name)[1].lower().replace('.', '')
        file_path = default_storage.save(f"temp_ml/{resume_file.name}", resume_file)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        resume_text = extract_text_from_file(full_path, file_ext)
        if not resume_text or not resume_text.strip():
            return Response({"error": "Could not extract text"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        predictor = get_ml_predictor()
        if predictor:
            result = predictor.calculate_metrics(resume_text, jd)
            score = result.match_score
            matched = result.matched_keywords
        else:
            score = 50.0
            matched = []
        verdict = "Shortlist" if score >= 60 else "Review"
        ml_record = MLAnalysis.objects.create(
            resume_filename=resume_file.name,
            job_description=jd,
            ml_score=score,
            matched_keywords=matched,
            verdict=verdict,
            method="hybrid_sbert_tfidf" if predictor else "fallback"
        )
        return Response({
            "match_score_percent": score,
            "matched_keywords": matched,
            "verdict": verdict,
            "method": "hybrid_sbert_tfidf" if predictor else "fallback",
            "analysis_id": ml_record.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"[ML_ANALYZE CRASH] {type(e).__name__}: {str(e)}")
        return Response({"error": "ML analysis failed", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if 'full_path' in locals() and os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
            except Exception as cleanup_err:
                print(f"Cleanup warning: {cleanup_err}")