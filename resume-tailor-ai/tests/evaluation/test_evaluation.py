"""Evaluation tests: Structure conformity and Anti-Hallucination rules."""
import pytest
from parsers.resume_parser import resume_parser
from parsers.jd_parser import jd_parser
from agents.crew_manager import career_crew
from models.schemas import CareerIntelligenceResult

SAMPLE_MD = """# Alex Morgan
Email: alex.morgan@example.com
Phone: +1 555 234 5678

## Summary
Software Engineer with expertise in Java, Python, and CrewAI.

## Skills
* Python
* Java
* CrewAI
* MySQL

## Projects
* Built an AI Resume Analyzer with CrewAI and Python.
"""

def test_full_pipeline_structure_and_anti_hallucination():
    resume = resume_parser.parse("candidate_resume.md", SAMPLE_MD.encode("utf-8"))
    jd = jd_parser.parse_text("Role: AI Systems Engineer. Required: Python, Docker, Kubernetes, AWS, CrewAI")

    result: CareerIntelligenceResult = career_crew.run_pipeline(resume, jd)

    # 1. Output Structure Validation
    assert result.ats_analysis.overall_ats_score > 0
    assert len(result.interview_questions) >= 3
    assert len(result.resume_optimization.items) >= 2

    # 2. Anti-Hallucination Integrity Check
    # Verify that 'Skills Safe to Highlight' only contains skills detected in candidate resume
    resume_skills_lower = {s.lower() for s in resume.skills}
    for safe_skill in result.skill_intelligence.skills_safe_to_highlight:
        # Must exist in candidate resume
        assert safe_skill.lower() in resume_skills_lower or safe_skill.lower() in resume.raw_text.lower()
