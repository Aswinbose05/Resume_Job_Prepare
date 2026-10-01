"""
FastAPI Routes for AI Resume Analyzer & Job Preparation System.
Implements secure REST endpoints with rate limiting, input validation, and static UI serving.
Powered by a pure CrewAI Multi-Agent Architecture.
"""
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.logger import logger
from security.file_validator import file_validator
from security.prompt_guard import prompt_guard
from security.ssrf_guard import ssrf_guard
from security.pii_sanitizer import pii_sanitizer
from security.rate_limiter import rate_limiter
from parsers.resume_parser import resume_parser
from parsers.jd_parser import jd_parser
from agents.crew_manager import career_crew
from models.schemas import CareerIntelligenceResult, MockInterviewEvaluation

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade AI Resume Analyzer & Job Preparation System powered by CrewAI"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to static frontend assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MockInterviewRequest(BaseModel):
    question: str
    user_answer: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the primary Web UI."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h2>AI Resume Analyzer & Job Preparation System UI initializing...</h2>")


@app.get("/api/health")
@app.get("/healthz")
async def health_check():
    """System health check and readiness."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "primary_provider": settings.LLM_PROVIDER,
        "security_controls": {
            "prompt_guard": settings.ENABLE_PROMPT_GUARD,
            "ssrf_protection": settings.ENABLE_SSRF_PROTECTION,
            "pii_masking": settings.ENABLE_PII_MASKING,
            "rate_limiting": settings.ENABLE_RATE_LIMITING
        }
    }


@app.post("/api/analyze")
async def analyze_profile(
    request: Request,
    resume_file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    job_url: Optional[str] = Form(None),
):
    """
    Main Analysis Endpoint:
    Accepts resume file (PDF, DOCX, MD, TXT) and target job description (text or URL).
    Passes through file validation, prompt injection detection, SSRF protection,
    and returns comprehensive ATS scoring, skill gap intelligence, and interview preparation.
    """
    client_ip = request.client.host if request.client else "anonymous"

    # 1. Rate Limiting Check
    if settings.ENABLE_RATE_LIMITING:
        allowed, retry_after = rate_limiter.is_allowed(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before submitting again."
            )

    # 2. Read and Validate Uploaded File
    try:
        content_bytes = await resume_file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Could not read uploaded file content.")

    file_scan = file_validator.validate_file(resume_file.filename or "resume.pdf", content_bytes)
    if not file_scan.is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=file_scan.block_reason or "File validation failed."
        )

    # 3. Parse Resume
    try:
        parsed_resume = resume_parser.parse(resume_file.filename or "resume.pdf", content_bytes)
    except Exception as e:
        logger.error(f"Error parsing resume: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")

    # 4. Prompt Guard Scan on Resume Content
    if settings.ENABLE_PROMPT_GUARD:
        guard_result = prompt_guard.scan_text(parsed_resume.raw_text, context_label="Uploaded Resume")
        if guard_result.blocked:
            logger.warning(f"Resume blocked by Prompt Guard: {guard_result.block_reason}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Security Policy Violation: {guard_result.block_reason}"
            )

    # 5. Process Job Description (URL with SSRF Guard or Direct Text)
    jd_data = None
    url_fetch_error = None
    if job_url and job_url.strip():
        safe_url, reason = ssrf_guard.validate_url(job_url.strip())
        if not safe_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or unsafe Job Posting URL: {reason}"
            )
        try:
            parsed_from_url, fetch_msg = jd_parser.fetch_and_parse_url(job_url.strip())
            if parsed_from_url:
                jd_data = parsed_from_url
            else:
                url_fetch_error = fetch_msg
        except Exception as e:
            logger.warning(f"Failed to fetch JD from URL ({e}).")
            url_fetch_error = str(e)

    # If user also or instead provided text, prioritize or enrich it
    if job_description and job_description.strip():
        if settings.ENABLE_PROMPT_GUARD:
            jd_guard = prompt_guard.scan_text(job_description, context_label="Job Description")
            if jd_guard.blocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Security Policy Violation in Job Description: {jd_guard.block_reason}"
                )
        text_jd = jd_parser.parse_text(job_description, source_url=job_url.strip() if job_url else None)
        if jd_data and not text_jd.company and jd_data.company:
            text_jd.company = jd_data.company
        jd_data = text_jd
    elif not jd_data and job_url and job_url.strip():
        # URL was provided but failed and no text was pasted
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to scrape job details from the provided URL ({url_fetch_error or 'protected by login/anti-bot'}). Please paste the Job Description text directly into the box."
        )
    elif not jd_data:
        # Fallback default target role from candidate's top skill profile
        jd_data = jd_parser.parse_text(
            f"Software Engineer role requiring expertise in: {', '.join(parsed_resume.skills[:8]) if parsed_resume.skills else 'Python, Backend, APIs'}"
        )

    # 6. Execute Multi-Agent Intelligence Pipeline via CrewAI
    try:
        result: CareerIntelligenceResult = career_crew.run_pipeline(parsed_resume, jd_data)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        logger.error(f"Unhandled pipeline execution error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while analyzing your profile. Please check that input data is valid."
        )


@app.post("/api/mock-interview/evaluate")
async def evaluate_mock_answer(req: MockInterviewRequest):
    """Evaluates candidate response to a specific interview question."""
    if not req.question or not req.user_answer:
        raise HTTPException(status_code=400, detail="Question and answer are required.")

    # Guard check on user response
    if settings.ENABLE_PROMPT_GUARD:
        guard_ans = prompt_guard.scan_text(req.user_answer, context_label="Candidate Answer")
        if guard_ans.blocked:
            raise HTTPException(status_code=403, detail="Security Rejection: Malicious instructions detected in answer.")

    evaluation: MockInterviewEvaluation = career_crew.evaluate_mock_answer(req.question, req.user_answer)
    return JSONResponse(content=evaluation.model_dump())
