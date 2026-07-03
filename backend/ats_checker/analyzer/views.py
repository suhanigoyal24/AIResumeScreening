from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
import os, re, traceback
from .models import Candidate, JobDescription, MatchScore, MLAnalysis
from .utils import extract_text_from_file, extract_skills, calculate_weighted_score, nlp

# Lazy ML predictor - loads only on first request, not at startup
_ml_predictor = None

def get_ml_predictor():
    global _ml_predictor
    if _ml_predictor is None:
        try:
            from .ml_engine.ml_predictor import ATSMLPredictor
            _ml_predictor = ATSMLPredictor()
            print("ML Predictor loaded successfully")
        except Exception as e:
            print(f"ML Predictor unavailable: {e}")
    return _ml_predictor


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
    from collections import Counter
    return [word for word, _ in Counter(filtered).most_common(max_keywords)]


# POST /api/upload/
# Requires JWT authentication
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_resume(request):
    print(f"\n{'='*60}")
    print(f"[UPLOAD] User: {request.user.username}")
    print(f"[UPLOAD] Resumes count: {len(request.FILES.getlist('resumes'))}")
    print(f"[UPLOAD] JD text length: {len(request.data.get('job_description', ''))}")
    print(f"{'='*60}\n")

    resumes = request.FILES.getlist('resumes')
    job_description_text = request.data.get('job_description', '').strip()
    jd_file = request.FILES.get('jd_file')
    session_id = request.data.get('session_id', f"session_{timezone.now().timestamp()}")

    if not resumes:
        return Response({"error": "No resume files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

    if not job_description_text and not jd_file:
        return Response({
            "error": "Missing job description",
            "detail": "Provide job description as text or upload a JD file"
        }, status=status.HTTP_400_BAD_REQUEST)

    jd_temp_path = None
    try:
        if jd_file and not job_description_text:
            jd_ext = os.path.splitext(jd_file.name)[1].lower()
            jd_temp_path = default_storage.save(f"jd_temp/{jd_file.name}", jd_file)
            jd_full_path = os.path.join(settings.MEDIA_ROOT, jd_temp_path)
            job_description_text = extract_text_from_file(jd_full_path, jd_ext[1:])

        if not job_description_text.strip():
            return Response({
                "error": "Could not extract job description text"
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    except Exception as jd_error:
        traceback.print_exc()
        return Response({
            "error": "Failed to process job description",
            "details": str(jd_error)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            resume_keywords = extract_keywords(resume_text)
            job_keywords = extract_keywords(job_description_text)

            matched_keywords = list(set(resume_keywords) & set(job_keywords))
            missing_keywords = list(set(job_keywords) - set(resume_keywords))

            resume_doc = nlp(resume_text)
            job_doc = nlp(job_description_text)
            base_result = calculate_weighted_score(
                resume_text, job_description_text,
                resume_skills, job_skills,
                resume_doc, job_doc
            )

            keyword_match_rate = len(matched_keywords) / max(len(job_keywords), 1)
            skill_match_rate = len(set(resume_skills) & set(job_skills)) / max(len(job_skills), 1)

            if predictor:
                try:
                    ml_result = predictor.predict(resume_text, job_description_text)
                    ml_score = ml_result['score']
                    final_score = round(ml_score * 0.85 + base_result['score'] * 0.15, 1)
                except Exception as ml_error:
                    print(f"ML prediction failed for {resume.name}: {ml_error}")
                    final_score = base_result['score']
            else:
                final_score = base_result['score']

            section_scores = {
                "skills": min(100, round(skill_match_rate * 100 + 5)),
                "experience": min(100, round(final_score * 0.9)),
                "education": min(100, round(final_score * 0.85 + 10)),
                "keywords": min(100, round(keyword_match_rate * 100))
            }

            recommendations = []
            if missing_keywords:
                recommendations.append(f"Add missing keywords: {', '.join(missing_keywords[:3])}")
            if final_score < 70:
                recommendations.append("Quantify achievements with metrics")
            if len(resume_skills) < len(job_skills) * 0.7:
                recommendations.append("Highlight more technical skills from the job description")
            recommendations.append("Use standard section headings: Experience, Skills, Education")

            candidate_name = resume.name.rsplit('.', 1)[0]
            candidate = Candidate.objects.create(
                name=candidate_name,
                resume_file=file_path,
                extracted_text=resume_text[:5000],
                extracted_skills=resume_skills,
                session_id=session_id
            )

            MatchScore.objects.create(
                candidate=candidate,
                score=final_score / 100,
                missing_skills=missing_keywords,
                matched_skills=matched_keywords
            )

            result.update({
                "success": True,
                "candidate_id": candidate.id,
                "score": final_score,
                "matched_keywords": matched_keywords[:15],
                "missing_keywords": missing_keywords[:15],
                "section_scores": section_scores,
                "recommendations": recommendations[:4],
                "scoring_method": "ml_hybrid" if predictor else "traditional"
            })

            print(f"[SUCCESS] {resume.name} - Score: {final_score}")

        except Exception as e:
            print(f"[ERROR processing {resume.name}] {str(e)}")
            traceback.print_exc()
            result["error"] = str(e)

        results.append(result)

    success_count = sum(1 for r in results if r.get("success"))
    failed_count = len(resumes) - success_count

    return Response({
        "session_id": session_id,
        "total_uploaded": len(resumes),
        "successful": success_count,
        "failed": failed_count,
        "results": results
    }, status=status.HTTP_200_OK)


# GET /api/candidates/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_candidates(request):
    try:
        candidates = Candidate.objects.all().order_by('-id')
        results = []

        for c in candidates:
            match_score = MatchScore.objects.filter(candidate=c).first()
            candidate_data = {
                "id": c.id,
                "name": c.name,
                "score": round((match_score.score * 100) if match_score else 0, 1),
                "skills": c.extracted_skills or [],
                "session_id": getattr(c, 'session_id', None)
            }
            if match_score and match_score.missing_skills:
                candidate_data["match_report"] = {
                    "matched_keywords": [s for s in (c.extracted_skills or []) if s not in (match_score.missing_skills or [])],
                    "missing_keywords": match_score.missing_skills or [],
                    "recommendations": [
                        f"Add missing skills: {', '.join(match_score.missing_skills[:3])}" if match_score.missing_skills else "Good skill coverage",
                        "Quantify achievements with metrics",
                        "Use standard section headings"
                    ]
                }
            results.append(candidate_data)

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": "Failed to load candidates"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET /api/dashboard/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    min_score = float(request.query_params.get('min_score', 0))
    all_candidates = Candidate.objects.all().order_by('-created_at')

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
                "skills_count": len(cand.extracted_skills or []),
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
                "session_id": getattr(cand, 'session_id', None)
            })

    total = Candidate.objects.count()
    avg_score = MatchScore.objects.aggregate(Avg('score'))['score__avg'] or 0
    passed = MatchScore.objects.filter(score__gte=0.6).count()

    summary = {
        "total_resumes": total,
        "avg_score": round((avg_score or 0) * 100, 1),
        "pass_rate_percent": round((passed / max(total, 1)) * 100, 1),
        "last_updated": timezone.now().isoformat()
    }

    comparison = [{
        "resume": c["name"][:25] + ("..." if len(c["name"]) > 25 else ""),
        "score": c["score"],
        "verdict": c["verdict"]
    } for c in candidates_list[:10]]

    return Response({
        "summary": summary,
        "charts": {"comparison": comparison},
        "candidates": candidates_list,
        "filter_applied": {"min_score": min_score}
    }, status=status.HTTP_200_OK)


# GET /api/dashboard/latest/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_latest(request):
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(minutes=10)
    recent_candidates = Candidate.objects.filter(created_at__gte=cutoff).order_by('-created_at')

    if not recent_candidates:
        return Response({
            "candidates": [],
            "summary": {"total_candidates": 0, "avg_score": 0, "pass_rate": 0},
            "charts": {"comparison": []}
        }, status=200)

    candidates_list = []
    for cand in recent_candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
            "verdict": "Shortlist" if (match_score.score or 0) >= 0.6 else "Review",
            "skills": cand.extracted_skills or [],
            "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
            "missing_keywords": (match_score.missing_skills if match_score else [])[:10],
            "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
            "session_id": getattr(cand, 'session_id', None)
        })

    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0
    passed = sum(1 for c in candidates_list if c["score"] >= 60)

    return Response({
        "summary": {
            "total_candidates": len(candidates_list),
            "avg_score": round(avg_score, 1),
            "pass_rate": round((passed / max(len(candidates_list), 1)) * 100, 1),
            "top_candidate": max(candidates_list, key=lambda x: x["score"])["name"] if candidates_list else None,
        },
        "candidates": candidates_list,
        "charts": {"comparison": [{
            "name": c["name"][:20] + ("..." if len(c["name"]) > 20 else ""),
            "score": c["score"],
            "verdict": c["verdict"]
        } for c in candidates_list]}
    }, status=200)


# GET /api/dashboard/session/<session_id>/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_by_session(request, session_id):
    candidates = Candidate.objects.filter(session_id=session_id).order_by('-created_at')

    if not candidates:
        return Response({
            "session_id": session_id,
            "candidates": [],
            "summary": {"total": 0, "avg_score": 0}
        }, status=200)

    candidates_list = []
    for cand in candidates:
        match_score = MatchScore.objects.filter(candidate=cand).first()
        candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "score": round((match_score.score or 0) * 100, 1) if match_score else 0,
            "verdict": "Shortlist" if (match_score.score or 0) >= 0.6 else "Review",
            "skills": cand.extracted_skills or [],
            "matched_keywords": (match_score.matched_skills if match_score else [])[:10],
            "analyzed_at": cand.created_at.isoformat() if cand.created_at else None
        })

    scores = [c["score"] for c in candidates_list if c["score"] > 0]
    avg_score = sum(scores) / len(scores) if scores else 0

    return Response({
        "session_id": session_id,
        "candidates": candidates_list,
        "summary": {
            "session_id": session_id,
            "total": len(candidates_list),
            "avg_score": round(avg_score, 1),
            "passed": sum(1 for c in candidates_list if c["score"] >= 60)
        }
    }, status=200)


# GET /api/dashboard/history/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_history(request):
    try:
        page = int(request.query_params.get('page', 1))
        page_size = 20
        search = request.query_params.get('search', '').lower()
        min_score = float(request.query_params.get('min_score', 0))

        candidates = Candidate.objects.all().order_by('-created_at')

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
                "session_id": str(getattr(cand, 'session_id', 'default')),
                "analyzed_at": cand.created_at.isoformat() if cand.created_at else None,
                "skills_count": len(cand.extracted_skills or []),
            })

        return Response({
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            },
            "filters_applied": {"search": search, "min_score": min_score}
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
            result = predictor.predict(resume_text, jd)
            score = result['score']
            matched = result['matched_keywords']
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
            method="ml_hybrid" if predictor else "fallback"
        )

        return Response({
            "match_score_percent": score,
            "matched_keywords": matched,
            "verdict": verdict,
            "method": "ml_hybrid" if predictor else "fallback",
            "analysis_id": ml_record.id
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"[ML_ANALYZE CRASH] {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        return Response({
            "error": "ML analysis failed",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        if 'full_path' in locals() and os.path.exists(full_path):
            try:
                os.remove(full_path)
                default_storage.delete(file_path)
            except Exception as cleanup_err:
                print(f"[DEBUG] Cleanup warning: {cleanup_err}")