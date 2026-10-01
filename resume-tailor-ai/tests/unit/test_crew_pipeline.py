"""
Unit and Integration Tests for CrewAI Multi-Agent Pipeline:
- Resume & JD Analysis
- Deterministic ATS & Domain Match
- Resume Tailor / STAR Optimizer
- Interview Question Preparation & Mock Simulator
- FastAPI Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.routes import app
from agents.crew_manager import career_crew
from parsers.resume_parser import resume_parser
from parsers.jd_parser import jd_parser
from models.schemas import CareerIntelligenceResult, MockInterviewEvaluation

client = TestClient(app)

SAMPLE_RESUME_TEXT = """
# Alex Morgan
Email: alex.morgan@example.com | Phone: +1 555 234 5678
LinkedIn: linkedin.com/in/alexmorgan | GitHub: github.com/alexmorgan

Summary:
Computer Science graduate with experience in Software Development, AI Applications, and Backend Development. Built end-to-end applications using Java, Spring Boot, Python, REST APIs, LangChain, CrewAI, and MySQL.

Skills:
Python, Java, MySQL, Machine Learning, CrewAI, LangChain, Docker, Git, REST API.

Experience:
- Developed an AI Resume Analyzer and Tailoring platform using CrewAI, LangChain, and Python.
- Built scalable REST APIs with Spring Boot and optimized relational database queries.
"""

SAMPLE_JD_TEXT = """
Job Title: Senior AI & Backend Systems Engineer
Company: CloudScale AI
Responsibilities:
- Build and scale multi-agent agentic workflows using CrewAI, LangChain, and FastAPI.
- Design containerized microservices deployed to AWS and Kubernetes clusters.
- Enforce strict AI application security, prompt injection defense, and OWASP LLM guardrails.

Required Qualifications:
- 2+ years experience in Python and Java.
- Proven hands-on experience with CrewAI and LangChain.
- Experience with Docker and REST APIs.
"""


def test_crewai_pipeline_execution():
    """Verifies that the CrewAI pipeline processes resume and JD into a complete CareerIntelligenceResult."""
    resume = resume_parser.parse("aswin_resume.md", SAMPLE_RESUME_TEXT.encode("utf-8"))
    jd = jd_parser.parse_text(SAMPLE_JD_TEXT)

    result: CareerIntelligenceResult = career_crew.run_pipeline(resume, jd)

    assert result.ats_analysis.overall_ats_score >= 0
    assert result.ats_analysis.overall_ats_score <= 100
    assert len(result.ats_analysis.matched_keywords) > 0
    assert len(result.skill_intelligence.strong_skills) > 0
    assert len(result.resume_optimization.items) > 0
    assert len(result.interview_questions) > 0


def test_mock_interview_evaluation():
    """Verifies that the mock interview evaluator grades user answers accurately."""
    question = "How do you coordinate multiple AI agents in CrewAI?"
    user_answer = "I define specialized agents with clear roles, goals, and backstories. Then I assign discrete tasks with structured output schemas, and coordinate them sequentially using Crew and Process.sequential."

    evaluation: MockInterviewEvaluation = career_crew.evaluate_mock_answer(question, user_answer)

    assert evaluation.overall_score >= 0
    assert evaluation.overall_score <= 100
    assert evaluation.technical_accuracy >= 1
    assert len(evaluation.feedback) > 10
    assert len(evaluation.improved_answer) > 10


def test_api_analyze_endpoint():
    """Verifies the /api/analyze endpoint returns 200 with complete CrewAI intelligence."""
    files = {"resume_file": ("test_resume.md", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/markdown")}
    data = {"job_description": SAMPLE_JD_TEXT}

    resp = client.post("/api/analyze", files=files, data=data)
    assert resp.status_code == 200

    payload = resp.json()
    assert "ats_analysis" in payload
    assert "skill_intelligence" in payload
    assert "resume_optimization" in payload
    assert "interview_questions" in payload


def test_api_mock_evaluate_endpoint():
    """Verifies the /api/mock-interview/evaluate endpoint."""
    resp = client.post("/api/mock-interview/evaluate", json={
        "question": "Explain how you design a REST API with Spring Boot.",
        "user_answer": "I use Spring MVC annotations like @RestController and @GetMapping, define DTOs for request and response validation, and connect repositories using Spring Data JPA."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "feedback" in data
