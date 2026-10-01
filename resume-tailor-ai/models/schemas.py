"""
Pydantic Schemas for AI Career Intelligence Platform.
Enforces strict type safety and structured outputs across all modules and agents.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SkillStatus(str, Enum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"

class ContactInfo(BaseModel):
    name: str = Field(default="Not detected")
    email: str = Field(default="Not detected")
    phone: str = Field(default="Not detected")
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

class ParsedResume(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = Field(default="Not detected")
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    raw_text: str = Field(default="")
    page_count: int = Field(default=1)
    candidate_domain: str = Field(default="Software Engineering")
    estimated_experience_years: float = Field(default=0.5)
    is_fresher_or_entry_level: bool = Field(default=True)

class JobDescriptionData(BaseModel):
    title: str = Field(default="Target Role")
    company: Optional[str] = None
    role_domain: str = Field(default="Software Engineering")
    min_experience_years: float = Field(default=0.0)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_requirements: str = Field(default="Not detected")
    education_requirements: str = Field(default="Not detected")
    responsibilities: List[str] = Field(default_factory=list)
    tools_and_frameworks: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    raw_text: str = Field(default="")

class RecommendedSkill(BaseModel):
    skill: str
    status: SkillStatus
    importance: str = Field(description="High, Medium, or Low")
    reason: str
    existing_related_skills: List[str] = Field(default_factory=list)
    recommended_learning_path: List[str] = Field(default_factory=list)

class SkillIntelligenceResult(BaseModel):
    existing_skills: List[str] = Field(default_factory=list)
    strong_skills: List[str] = Field(default_factory=list)
    partial_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    skill_breakdown: List[RecommendedSkill] = Field(default_factory=list)
    skills_safe_to_highlight: List[str] = Field(default_factory=list)
    skills_to_learn: List[str] = Field(default_factory=list)

class ATSScoreBreakdown(BaseModel):
    keyword_coverage_score: int = Field(default=0, ge=0, le=100)
    technical_skills_score: int = Field(default=0, ge=0, le=100)
    experience_alignment_score: int = Field(default=0, ge=0, le=100)
    education_alignment_score: int = Field(default=0, ge=0, le=100)
    formatting_score: int = Field(default=0, ge=0, le=100)

class ATSAnalysisResult(BaseModel):
    overall_ats_score: int = Field(default=0, ge=0, le=100)
    breakdown: ATSScoreBreakdown = Field(default_factory=ATSScoreBreakdown)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    formatting_risks: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    scoring_rationale: str = Field(default="")

class MatchCategories(BaseModel):
    overall_match: int = Field(default=0, ge=0, le=100)
    technical_match: int = Field(default=0, ge=0, le=100)
    ai_ml_match: int = Field(default=0, ge=0, le=100)
    backend_match: int = Field(default=0, ge=0, le=100)
    cloud_devops_match: int = Field(default=0, ge=0, le=100)
    experience_match: str = Field(default="Partial")
    education_match: str = Field(default="Matched")
    domain_match: str = Field(default="Matched")
    seniority_match: str = Field(default="Aligned")

class ResumeOptimizationItem(BaseModel):
    section: str
    original: str
    suggested: str
    why_this_is_better: str
    keywords_added: List[str] = Field(default_factory=list)

class ResumeOptimizationResult(BaseModel):
    items: List[ResumeOptimizationItem] = Field(default_factory=list)
    full_tailored_markdown: str = Field(default="")

class InterviewQuestion(BaseModel):
    category: str = Field(description="Technical, System Design, Behavioral, Project-based, AI/ML, HR")
    question: str
    talking_points: List[str] = Field(default_factory=list)
    context_source: str = Field(default="Resume project / target JD requirement")

class MockInterviewEvaluation(BaseModel):
    technical_accuracy: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    communication: int = Field(ge=0, le=10)
    overall_score: int = Field(ge=0, le=100)
    feedback: str
    improved_answer: str

class CareerIntelligenceResult(BaseModel):
    resume_data: ParsedResume
    jd_data: JobDescriptionData
    ats_analysis: ATSAnalysisResult
    match_categories: MatchCategories
    skill_intelligence: SkillIntelligenceResult
    resume_optimization: ResumeOptimizationResult
    interview_questions: List[InterviewQuestion] = Field(default_factory=list)
    company_interview_pattern: Optional[Dict[str, Any]] = None


