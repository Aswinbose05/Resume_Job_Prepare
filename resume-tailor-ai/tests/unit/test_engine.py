"""Unit tests for ATS Scorer and Skill Intelligence Engine."""
import pytest
from parsers.resume_parser import resume_parser
from parsers.jd_parser import jd_parser
from engine.ats_scorer import ats_scorer
from engine.skill_engine import skill_engine
from models.schemas import SkillStatus

RESUME_TEXT = """# Developer One
Email: dev@example.com
Phone: +91 9999999999

## Summary
Software engineer with experience in Python, MySQL, and Docker.

## Skills
* Python
* MySQL
* Docker
* Git

## Projects
* Scalable backend in Python and Docker.
"""

JD_TEXT = """
Role: Python Cloud Engineer
Required skills: Python, Docker, Kubernetes, AWS, MySQL
"""

def test_ats_scorer_deterministic_output():
    res = resume_parser.parse("res.md", RESUME_TEXT.encode("utf-8"))
    jd = jd_parser.parse_text(JD_TEXT)
    
    ats1, _ = ats_scorer.evaluate(res, jd)
    ats2, _ = ats_scorer.evaluate(res, jd)

    # Deterministic test: identical inputs must yield identical scores
    assert ats1.overall_ats_score == ats2.overall_ats_score
    assert 50 <= ats1.overall_ats_score <= 90
    assert "Python" in ats1.matched_keywords
    assert "Kubernetes" in ats1.missing_keywords
    assert ats1.breakdown.formatting_score >= 80

def test_skill_intelligence_classification():
    res = resume_parser.parse("res.md", RESUME_TEXT.encode("utf-8"))
    jd = jd_parser.parse_text(JD_TEXT)
    
    intel = skill_engine.analyze(res, jd)
    
    # Python is present in resume
    assert "Python" in intel.strong_skills
    # Kubernetes is required by JD, and candidate has Docker foundation -> Partial
    assert "Kubernetes" in intel.partial_skills or "Kubernetes" in intel.missing_skills
    # Check that skills to learn are populated
    assert len(intel.skills_to_learn) > 0
    # Anti-hallucination check: Safe to highlight must NOT contain missing skills
    for safe in intel.skills_safe_to_highlight:
        assert safe not in intel.missing_skills
