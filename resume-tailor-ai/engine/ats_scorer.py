"""
Deterministic ATS (Applicant Tracking System) Scoring Engine.
Calculates explainable, rule-based ATS metrics, domain compatibility, and seniority alignment.
"""
import re
from typing import List, Dict, Set, Tuple
from models.schemas import (
    ParsedResume, JobDescriptionData, ATSAnalysisResult, ATSScoreBreakdown, MatchCategories
)
from core.logger import logger

class ATSScorer:
    """Deterministic, explainable Applicant Tracking System scoring engine with domain and seniority validation."""

    @classmethod
    def evaluate(cls, resume: ParsedResume, jd: JobDescriptionData) -> Tuple[ATSAnalysisResult, MatchCategories]:
        """
        Executes deterministic rules across 5 weighted dimensions:
        1. Keyword Coverage (35%)
        2. Technical/Role Skill Match (25%)
        3. Experience & Seniority Alignment (20%)
        4. Education Alignment (10%)
        5. Formatting & Structure (10%)
        """
        resume_text_lower = resume.raw_text.lower()
        resume_skills_lower = {s.lower() for s in resume.skills}
        
        # Collect JD requirements
        jd_skills_lower = [s.lower() for s in jd.required_skills]
        if not jd_skills_lower:
            # Fallback extraction from raw JD if required_skills was somehow empty
            jd_words = re.findall(r'\b[A-Za-z]{3,}\b', jd.raw_text.lower())
            jd_skills_lower = list(set([w for w in jd_words if w in ["sales", "quota", "crm", "erp", "engineering", "python", "java", "cloud"]]))

        # 1. Keyword Alignment
        matched_skills = []
        missing_skills = []

        for skill in jd.required_skills:
            s_lower = skill.lower()
            if s_lower in resume_skills_lower or re.search(r'\b' + re.escape(s_lower) + r'\b', resume_text_lower):
                matched_skills.append(skill)
            else:
                missing_skills.append(skill)

        total_req = len(jd.required_skills)
        if total_req > 0:
            coverage_ratio = len(matched_skills) / total_req
            keyword_score = int(coverage_ratio * 100)
        else:
            keyword_score = 20
            matched_skills = []
            missing_skills = ["Role Requirements"]

        # 2. Technical / Functional Role Skill Score
        if total_req > 0:
            tech_score = int(coverage_ratio * 100)
        else:
            tech_score = 15

        # 3. Experience & Seniority Alignment
        formatting_risks = []
        suggestions = []
        
        cand_years = getattr(resume, "estimated_experience_years", 0.5)
        req_years = getattr(jd, "min_experience_years", 0.0)

        if req_years >= 3.0:
            # Role requires significant experience
            exp_ratio = min(1.0, cand_years / req_years)
            exp_score = max(5, int(exp_ratio * 100))
            if cand_years < (req_years * 0.5):
                exp_match_label = f"Seniority Mismatch (Requires {req_years:.0f}+ yrs, candidate ~{cand_years:.1f} yr)"
                formatting_risks.append(f"Major Seniority Gap: Target role requires {req_years:.0f}+ years, but candidate profile shows entry-level/early career (~{cand_years:.1f} years).")
                suggestions.append(f"Target roles aligned with your experience level (0-2 years, Junior/Associate) to maximize interview conversion.")
            else:
                exp_match_label = f"Partial Seniority ({cand_years:.1f} of {req_years:.0f}+ yrs)"
        else:
            # Entry level / Fresher friendly role
            if cand_years >= 1.0 or len(resume.projects) >= 2 or resume.experience:
                exp_score = 90
                exp_match_label = "Strong Fit (Entry Level)"
            else:
                exp_score = 70
                exp_match_label = "Moderate (Fresher)"

        # 4. Education Alignment
        edu_score = 70
        edu_label = "Partially Aligned"
        if resume.education or any(k in resume_text_lower for k in ["b.e", "b.tech", "bachelor", "master", "computer science"]):
            edu_score = 95
            edu_label = "Strongly Matched"

        # 5. Domain Alignment & Penalties
        cand_domain = getattr(resume, "candidate_domain", "Software & AI Engineering")
        role_domain = getattr(jd, "role_domain", "Software Engineering")
        
        is_domain_mismatch = False
        if ("sales" in role_domain.lower() or "business development" in role_domain.lower()) and "engineering" in cand_domain.lower():
            is_domain_mismatch = True
        elif ("engineering" in role_domain.lower()) and ("sales" in cand_domain.lower()):
            is_domain_mismatch = True

        domain_match_label = "Domain Aligned"
        domain_penalty = 1.0
        if is_domain_mismatch:
            domain_penalty = 0.35  # Severe penalty for applying to completely different profession
            domain_match_label = f"Domain Mismatch ({cand_domain} vs {role_domain})"
            formatting_risks.insert(0, f"Critical Domain Mismatch: Target position is in '{role_domain}', while your resume reflects '{cand_domain}'.")
            suggestions.insert(0, f"Ensure you are applying to roles in your domain ({cand_domain}), or build a dedicated transition resume highlighting transferable sales/leadership competencies.")

        # 6. Formatting & Structure Verification
        formatting_score = 100
        if resume.contact.email == "Not detected":
            formatting_score -= 20
            formatting_risks.append("Missing or unparseable Email address.")
            suggestions.append("Add a clearly visible standard email address at the top.")
        if resume.contact.phone == "Not detected":
            formatting_score -= 15
            formatting_risks.append("Missing contact telephone number.")
            suggestions.append("Include your contact phone number with country code.")
        if not resume.contact.linkedin and not resume.contact.github:
            formatting_score -= 10
            formatting_risks.append("No professional profile links (LinkedIn/GitHub) detected.")
            suggestions.append("Include clickable links to your LinkedIn and GitHub profiles.")

        if resume.page_count > 3:
            formatting_score -= 15
            formatting_risks.append(f"Resume length is {resume.page_count} pages (Recommended: 1-2 pages for technical roles).")
            suggestions.append("Condense project and experience bullet points to maintain a 1-2 page layout.")

        formatting_score = max(30, formatting_score)

        # Calculate Overall Raw Weighted Score
        raw_overall = (
            (keyword_score * 0.35) +
            (tech_score * 0.25) +
            (exp_score * 0.20) +
            (edu_score * 0.10) +
            (formatting_score * 0.10)
        )

        # Apply domain compatibility penalty
        final_overall_ats = int(raw_overall * domain_penalty)
        final_overall_ats = min(100, max(5, final_overall_ats))

        # Overall Match percentage
        overall_match_pct = int(((keyword_score + tech_score) / 2) * domain_penalty)
        overall_match_pct = min(100, max(5, overall_match_pct))

        breakdown = ATSScoreBreakdown(
            keyword_coverage_score=keyword_score,
            technical_skills_score=tech_score,
            experience_alignment_score=exp_score,
            education_alignment_score=edu_score,
            formatting_score=formatting_score
        )

        rationale = (
            f"ATS Score of {final_overall_ats}/100. "
            f"Keyword Coverage: {keyword_score}% (weight 35%), Technical Alignment: {tech_score}% (weight 25%), "
            f"Experience/Seniority: {exp_score}% (weight 20%, {exp_match_label}), "
            f"Education: {edu_score}% (weight 10%), Formatting: {formatting_score}% (weight 10%)."
        )
        if is_domain_mismatch:
            rationale += f" [Domain Mismatch Factor applied: {domain_penalty:.2f} due to {cand_domain} vs {role_domain}]."

        ats_result = ATSAnalysisResult(
            overall_ats_score=final_overall_ats,
            breakdown=breakdown,
            matched_keywords=matched_skills,
            missing_keywords=missing_skills,
            formatting_risks=formatting_risks,
            improvement_suggestions=suggestions,
            scoring_rationale=rationale
        )

        # Domain breakdown for dashboard cards
        ai_ml_tech = {"machine learning", "rag", "crewai", "langchain", "vector databases", "nlp", "deep learning", "pytorch", "tensorflow"}
        backend_tech = {"python", "java", "spring boot", "fastapi", "django", "mysql", "postgresql", "rest api", "microservices"}
        cloud_tech = {"docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "terraform", "linux", "cloud", "saas"}

        ai_match = cls._compute_category_match(resume_skills_lower, jd_skills_lower, ai_ml_tech)
        backend_match = cls._compute_category_match(resume_skills_lower, jd_skills_lower, backend_tech)
        cloud_match = cls._compute_category_match(resume_skills_lower, jd_skills_lower, cloud_tech)

        match_cats = MatchCategories(
            overall_match=overall_match_pct,
            technical_match=tech_score,
            ai_ml_match=ai_match,
            backend_match=backend_match,
            cloud_devops_match=cloud_match,
            experience_match=exp_match_label,
            education_match=edu_label,
            domain_match=domain_match_label,
            seniority_match=exp_match_label
        )

        return ats_result, match_cats

    @staticmethod
    def _compute_category_match(resume_skills: Set[str], jd_skills: List[str], category_set: Set[str]) -> int:
        """Calculates percentage match within a specific domain category."""
        target_in_cat = [s for s in jd_skills if s in category_set]
        if not target_in_cat:
            # If JD didn't ask for this domain at all, match is 0% for this role
            return 0

        matched = [s for s in target_in_cat if s in resume_skills]
        return int((len(matched) / len(target_in_cat)) * 100)

ats_scorer = ATSScorer()
