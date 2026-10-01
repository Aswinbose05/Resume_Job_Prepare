"""
Job Description Parser & Normalizer.
Extracts requirements, skills, qualifications, responsibilities, role domains, and experience thresholds.
"""
import re
from typing import List, Optional, Tuple, Set
from core.logger import logger
from security.ssrf_guard import ssrf_guard
from models.schemas import JobDescriptionData

# Comprehensive Skill Taxonomies by Domain
DOMAIN_SKILLS = {
    "software_engineering": [
        "python", "java", "c++", "c#", "golang", "rust", "javascript", "typescript",
        "fastapi", "flask", "django", "spring boot", "react", "vue", "angular", "node.js",
        "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "sqlite",
        "rest api", "graphql", "microservices", "sql", "nosql", "git"
    ],
    "ai_data": [
        "machine learning", "deep learning", "nlp", "rag", "langchain", "crewai", "vector databases",
        "pandas", "numpy", "pytorch", "tensorflow", "spark", "hadoop", "snowflake", "data modeling"
    ],
    "devops_cloud": [
        "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "linux", "terraform",
        "kafka", "rabbitmq", "helm", "cloud"
    ],
    "sales_business": [
        "software sales", "enterprise software", "b2b sales", "saas", "crm", "erp",
        "account management", "pipeline management", "quota", "revenue", "prospecting",
        "contract negotiation", "client relationship", "business development", "demand generation",
        "sap solutions", "solution selling", "c-level", "deal closing", "stakeholder management",
        "territory management", "business planning"
    ],
    "product_management": [
        "product roadmap", "user stories", "agile", "scrum", "product strategy",
        "wireframing", "market research", "kpis", "feature prioritization", "sprint planning"
    ]
}

ROLE_TITLES_PATTERN = re.compile(
    r'(?i)\b(?:senior|lead|principal|staff|junior|expert|associate|vice president|vp|director|manager)?\s*'
    r'(?:program lead|account executive|sales director|sales manager|business development manager|'
    r'software engineer|full stack developer|backend developer|frontend developer|ai engineer|'
    r'data scientist|data engineer|solutions architect|devops engineer|product manager|cloud architect|scrum master)\b'
)

class JobDescriptionParser:
    """Parses, normalizes, and extracts structured fields from job postings across diverse industry domains."""

    @classmethod
    def _extract_company(cls, text: str, url: Optional[str] = None) -> str:
        """Extracts company name from text or URL."""
        # 1. Direct patterns in text
        patterns = [
            r'(?i)\bat\s+([A-Z][A-Za-z0-9&.\-]{1,25})\b,\s+we\b',  # "At SAP, we..."
            r'(?i)\bcompany\s*[:\-]\s*([A-Za-z0-9&.\-\s]{2,30})',
            r'(?i)\babout\s+([A-Z][A-Za-z0-9&.\-]{1,25})\b',        # "About SAP"
            r'(?i)\bjoin\s+(?:the\s+)?([A-Z][A-Za-z0-9&.\-]{1,25})\s+team\b',
            r'(?i)\b([A-Z][A-Za-z0-9&.\-]{1,20})\s+is\s+(?:an\s+equal|seeking|looking|hiring)\b'
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in ["the", "a", "our", "this", "job", "career"]:
                    return cand

        # 2. Check URL hostname
        if url:
            try:
                from urllib.parse import urlparse
                hostname = urlparse(url).hostname or ""
                parts = hostname.split(".")
                for part in parts:
                    if part.lower() not in ["www", "jobs", "careers", "com", "org", "net", "co", "in", "io", "ai", "linkedin"]:
                        return part.upper() if len(part) <= 4 else part.title()
            except Exception:
                pass

        return "Target Company"

    @classmethod
    def parse_text(cls, text: str, source_url: Optional[str] = None) -> JobDescriptionData:
        """Parses raw text of a job description with comprehensive domain recognition."""
        if not text or not text.strip():
            return JobDescriptionData(raw_text="")

        text_clean = text.strip()
        lines = [l.strip() for l in text_clean.splitlines() if l.strip()]

        # 1. Job Title & Company Extraction
        title = cls._extract_job_title(text_clean, lines)
        company = cls._extract_company(text_clean, source_url)

        # 2. Domain & Skills Extraction
        required_skills, role_domain = cls._extract_skills_and_domain(text_clean, lines)

        # 3. Experience Requirements & Numeric Min Years
        exp_text, min_years = cls._extract_experience(text_clean)

        # 4. Education Requirements
        education_requirements = cls._extract_education(text_clean)

        # 5. Extract Responsibilities
        responsibilities = cls._extract_responsibilities(lines)

        # 6. Tools and Frameworks
        tools = [s for s in required_skills if s.lower() in [
            "docker", "kubernetes", "aws", "git", "ci/cd", "terraform", "kafka", "crm", "erp", "sap solutions", "mysql", "react"
        ]]

        # 7. Soft skills
        soft_skills = cls._extract_soft_skills(text_clean)

        return JobDescriptionData(
            title=title,
            company=company,
            role_domain=role_domain,
            min_experience_years=min_years,
            required_skills=required_skills,
            responsibilities=responsibilities[:10],
            tools_and_frameworks=tools,
            soft_skills=soft_skills,
            experience_requirements=exp_text,
            education_requirements=education_requirements,
            raw_text=text_clean
        )

    @classmethod
    def _extract_job_title(cls, full_text: str, lines: List[str]) -> str:
        """Extracts a concise, realistic job title instead of full sentences."""
        # 1. Check for explicit "Title:" or "Role:" or "Requisition:"
        match = re.search(r'(?i)(?:job title|role|position|title)\s*[:\-]\s*([A-Za-z0-9\s\-/&]+)', full_text)
        if match:
            cand = match.group(1).split("\n")[0].strip()
            if 3 < len(cand) < 60:
                return cand.title()

        # 2. Check for known role title keywords in the first 500 characters
        role_match = ROLE_TITLES_PATTERN.search(full_text[:600])
        if role_match:
            return role_match.group(0).strip().title()

        # 3. Fallback: inspect top lines
        for line in lines[:4]:
            clean_line = re.sub(r'^[#*_\-\s]+', '', line)
            # Avoid long descriptive sentences
            if len(clean_line.split()) <= 6 and not clean_line.endswith("."):
                return clean_line.title()

        return "Target Role"

    @classmethod
    def _extract_skills_and_domain(cls, text: str, lines: List[str]) -> Tuple[List[str], str]:
        """Identifies skills from taxonomy and requirements sections, and determines primary role domain."""
        text_lower = text.lower()
        extracted_skills: Set[str] = set()
        domain_counts = {dom: 0 for dom in DOMAIN_SKILLS}

        # 1. Scan across all domain dictionaries
        for dom, skills in DOMAIN_SKILLS.items():
            for skill in skills:
                if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                    domain_counts[dom] += 1
                    extracted_skills.add(skill.title() if len(skill) > 3 else skill.upper())

        # 2. Extract explicit requirements from "What You Bring" / "Qualifications" sections
        capture = False
        for line in lines:
            if re.search(r'(?i)(what you bring|qualifications|requirements|must have|skills required)', line):
                capture = True
                continue
            if capture:
                if re.search(r'(?i)(what we offer|benefits|about us|bring out your best|equal opportunity)', line):
                    break
                # Process bullet items
                clean_bullet = re.sub(r'^[-*•\d.]+\s*', '', line).strip()
                if 5 < len(clean_bullet) < 100:
                    # Look for key competencies in bullet
                    if any(w in clean_bullet.lower() for w in ["sales", "negotiation", "contract", "quota", "lead", "pipeline"]):
                        extracted_skills.add("Enterprise Software Sales")
                        extracted_skills.add("Contract Negotiation")
                        domain_counts["sales_business"] += 3
                    if any(w in clean_bullet.lower() for w in ["crm", "customer relationship", "account"]):
                        extracted_skills.add("Account Management")
                        extracted_skills.add("CRM")
                        domain_counts["sales_business"] += 2

        # 3. Determine primary role domain
        primary_domain = "Software Engineering"
        max_domain = max(domain_counts, key=domain_counts.get)
        if domain_counts[max_domain] > 0:
            domain_labels = {
                "software_engineering": "Software Engineering",
                "ai_data": "AI & Data Engineering",
                "devops_cloud": "DevOps & Cloud Infrastructure",
                "sales_business": "Enterprise Sales & Account Leadership",
                "product_management": "Product Management"
            }
            primary_domain = domain_labels.get(max_domain, "Software Engineering")

        # Fallback if no specific skills matched
        if not extracted_skills:
            if "sales" in text_lower or "quota" in text_lower:
                extracted_skills.update(["Enterprise Software Sales", "Account Management", "Contract Negotiation", "SaaS Solutions"])
                primary_domain = "Enterprise Sales & Account Leadership"
            else:
                extracted_skills.update(["Software Engineering", "Problem Solving", "System Architecture"])

        return sorted(list(extracted_skills)), primary_domain

    @classmethod
    def _extract_experience(cls, text: str) -> Tuple[str, float]:
        """Extracts required experience phrase and numeric minimum years required."""
        match = re.search(r'(\d+[\+]?)\s*(?:to\s*\d+)?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text, re.IGNORECASE)
        if match:
            raw_str = match.group(0)
            years_str = match.group(1).replace("+", "")
            try:
                min_years = float(years_str)
            except ValueError:
                min_years = 1.0
            return raw_str, min_years

        # Look for senior / executive phrasing
        if re.search(r'(?i)\b(senior|lead|principal|director|executive|15\+)\b', text):
            return "Senior / Lead (5+ years required)", 5.0

        if re.search(r'(?i)\b(entry level|fresher|graduate|intern)\b', text):
            return "Entry Level / 0-2 years", 0.0

        return "Not explicitly specified", 1.0

    @classmethod
    def _extract_education(cls, text: str) -> str:
        """Extracts required education credentials."""
        match = re.search(r'(?i)(bachelor|master|phd|b\.?e\.?|b\.?tech|computer science|degree in|bachelor equivalent:\s*yes)', text)
        if match:
            return match.group(0).title()
        return "Degree or equivalent experience"

    @classmethod
    def _extract_responsibilities(cls, lines: List[str]) -> List[str]:
        """Captures up to 8 core role responsibilities."""
        responsibilities = []
        capture = False
        for line in lines:
            if re.search(r'(?i)(responsibilities|what you(?:\'ll| will) do|primary responsibilities|key duties)', line):
                capture = True
                continue
            if capture:
                if re.search(r'(?i)(qualifications|what you bring|requirements|skills|benefits)', line):
                    break
                if line.startswith(("-", "*", "•", "1", "2", "3", "4", "5")) or (line and len(line) > 30 and line[0].isupper()):
                    cleaned = re.sub(r'^[-*•\d.]+\s*', '', line).strip()
                    if 15 < len(cleaned) < 200:
                        responsibilities.append(cleaned)
        return responsibilities[:8]

    @classmethod
    def _extract_soft_skills(cls, text: str) -> List[str]:
        softs = []
        common = ["leadership", "communication", "negotiation", "collaboration", "teamwork", "analytical thinking", "strategic planning", "customer acumen"]
        text_lower = text.lower()
        for s in common:
            if re.search(r'\b' + re.escape(s) + r'\b', text_lower):
                softs.append(s.title())
        return softs

    @classmethod
    def fetch_and_parse_url(cls, url: str) -> Tuple[Optional[JobDescriptionData], str]:
        """Safely fetches a job description URL after SSRF validation."""
        is_safe, msg = ssrf_guard.is_safe_url(url)
        if not is_safe:
            return None, f"Security Warning: {msg}"

        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, f"Failed to fetch job URL: HTTP {resp.status_code}"

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator="\n")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            cleaned_text = "\n".join(lines)

            if len(cleaned_text) < 100:
                return None, "Retrieved page contains insufficient text or blocked by anti-bot."

            return cls.parse_text(cleaned_text, source_url=url), "Success"

        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None, f"Network or parsing error: {e}"

    @classmethod
    def parse_url(cls, url: str) -> Optional[JobDescriptionData]:
        """Convenience method returning parsed JobDescriptionData or None."""
        data, _ = cls.fetch_and_parse_url(url)
        return data

jd_parser = JobDescriptionParser()
