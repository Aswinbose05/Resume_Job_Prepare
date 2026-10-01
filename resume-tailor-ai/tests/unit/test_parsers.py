"""Unit tests for Resume and Job Description Parsers."""
import pytest
from parsers.resume_parser import resume_parser
from parsers.jd_parser import jd_parser

SAMPLE_RESUME_MD = """# Alex Smith
Email: alex.smith@example.com
Phone: +1 555-123-4567
LinkedIn: linkedin.com/in/alexsmith

## Professional Summary
Experienced Software Engineer specializing in Python, REST APIs, and Docker.

## Skills
* Python
* Java
* Docker
* MySQL
* FastAPI

## Projects
* Built an AI Resume Analyzer using Python and FastAPI.
"""

def test_resume_parser_contact_and_skills():
    resume = resume_parser.parse("resume.md", SAMPLE_RESUME_MD.encode("utf-8"))
    assert resume.contact.name == "Alex Smith"
    assert resume.contact.email == "alex.smith@example.com"
    assert "Python" in resume.skills
    assert "FastAPI" in resume.skills or "Fastapi" in resume.skills
    assert resume.summary != "Not detected"

def test_resume_parser_missing_fields_graceful():
    sparse_text = "Some random notes without contact info."
    resume = resume_parser.parse("notes.txt", sparse_text.encode("utf-8"))
    assert resume.contact.email == "Not detected"
    assert resume.contact.phone == "Not detected"

def test_jd_parser_skill_extraction():
    jd_text = """
    Job Title: Senior AI Systems Engineer
    Responsibilities:
    - Build scalable microservices with Python and FastAPI.
    - Deploy containerized workloads on Kubernetes and AWS.
    Qualifications:
    - 3+ years experience with Python, Docker, Kubernetes, and AWS.
    """
    jd = jd_parser.parse_text(jd_text)
    assert "Python" in jd.required_skills
    assert "Docker" in jd.required_skills
    assert "Kubernetes" in jd.required_skills
    assert "AWS" in jd.required_skills
    assert "3+ years" in jd.experience_requirements.lower() or "3+" in jd.experience_requirements
