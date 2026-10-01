"""
Multi-Format Resume Parser.
Supports PDF, DOCX, Markdown, and TXT documents.
Performs deterministic structure analysis without hallucinating missing data.
"""
import io
import re
from typing import List, Dict, Any, Optional
from core.logger import logger
from models.schemas import ParsedResume, ContactInfo

# Section Header Signatures
SECTION_PATTERNS = {
    "summary": re.compile(r'(?i)^(?:#+\s*)?(?:professional\s+)?summary|profile|about\s+me|objective'),
    "skills": re.compile(r'(?i)^(?:#+\s*)?(?:technical\s+)?skills|technologies|competencies|tech\s+stack'),
    "experience": re.compile(r'(?i)^(?:#+\s*)?(?:work\s+)?experience|employment|work\s+history|professional\s+experience'),
    "projects": re.compile(r'(?i)^(?:#+\s*)?projects|personal\s+projects|key\s+projects|academic\s+projects'),
    "education": re.compile(r'(?i)^(?:#+\s*)?education|academic\s+background|qualifications'),
    "certifications": re.compile(r'(?i)^(?:#+\s*)?certifications|courses|licenses|credentials'),
}

class ResumeParser:
    """Extracts raw text, contact information, and structured sections from resumes."""

    @classmethod
    def parse(cls, filename: str, content_bytes: bytes) -> ParsedResume:
        """Parses document bytes based on file extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
        
        raw_text = ""
        page_count = 1

        if ext == "pdf":
            raw_text, page_count = cls._parse_pdf(content_bytes)
        elif ext == "docx":
            raw_text = cls._parse_docx(content_bytes)
        else:  # md or txt
            raw_text = cls._parse_text(content_bytes)

        if not raw_text.strip():
            logger.warning(f"Extracted empty text from file: {filename}")

        return cls._structure_resume(raw_text, page_count)

    @classmethod
    def _parse_pdf(cls, content_bytes: bytes) -> tuple[str, int]:
        """Extracts text from PDF bytes using pdfplumber with fallback."""
        text_parts = []
        page_count = 1
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    txt = page.extract_text()
                    if txt:
                        text_parts.append(txt)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed, falling back to pypdf: {e}")
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                page_count = len(reader.pages)
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        text_parts.append(txt)
            except Exception as e2:
                logger.error(f"PDF extraction error: {e2}")

        return "\n\n".join(text_parts), page_count

    @classmethod
    def _parse_docx(cls, content_bytes: bytes) -> str:
        """Extracts text from DOCX bytes using python-docx."""
        text_parts = []
        try:
            import docx
            doc = docx.Document(io.BytesIO(content_bytes))
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        text_parts.append(" | ".join(row_text))
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
        return "\n".join(text_parts)

    @classmethod
    def _parse_text(cls, content_bytes: bytes) -> str:
        """Extracts text from UTF-8/ASCII bytes."""
        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Text decoding failed: {e}")
            return ""

    @classmethod
    def _structure_resume(cls, text: str, page_count: int) -> ParsedResume:
        """Extracts contact, skills, and sections deterministically."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Contact Information Extraction
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text)
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}', text)
        linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
        github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[\w-]+', text, re.IGNORECASE)
        
        # Name detection: look at first 3 non-empty lines for typical name header
        detected_name = "Not detected"
        for candidate in lines[:4]:
            candidate_clean = re.sub(r'^[#*_\-\s]+', '', candidate).strip()
            # If line has no email, no phone, no url, and is short, it's likely the candidate name
            if candidate_clean and len(candidate_clean.split()) <= 4 and "@" not in candidate_clean and "http" not in candidate_clean:
                detected_name = candidate_clean
                break

        contact = ContactInfo(
            name=detected_name,
            email=email_match.group(0) if email_match else "Not detected",
            phone=phone_match.group(0) if phone_match else "Not detected",
            linkedin=linkedin_match.group(0) if linkedin_match else None,
            github=github_match.group(0) if github_match else None,
        )

        # 2. Section Partitioning
        sections: Dict[str, List[str]] = {k: [] for k in SECTION_PATTERNS}
        current_section = None

        for line in lines:
            line_clean = re.sub(r'^[#*_\-\s]+', '', line).strip()
            # Check if this line is a section header
            matched_header = None
            for sec_name, pattern in SECTION_PATTERNS.items():
                if pattern.match(line_clean) and len(line_clean.split()) <= 5:
                    matched_header = sec_name
                    break
            
            if matched_header:
                current_section = matched_header
                continue

            if current_section:
                sections[current_section].append(line)

        # 3. Extract Skills as Clean List
        raw_skills_text = "\n".join(sections["skills"])
        skills_list = cls._extract_skills_from_text(raw_skills_text or text)

        summary_text = "\n".join(sections["summary"]).strip() or "Not detected"

        # Format structured experience/projects/education
        experience_items = [{"raw": item} for item in sections["experience"]] if sections["experience"] else []
        project_items = [{"raw": item} for item in sections["projects"]] if sections["projects"] else []
        education_items = [{"raw": item} for item in sections["education"]] if sections["education"] else []
        cert_items = sections["certifications"] if sections["certifications"] else []

        all_links = re.findall(r'https?://[^\s)\]]+', text)

        # Experience & Domain Estimation
        text_lower = text.lower()
        is_fresher = bool(re.search(r'(?i)\b(graduate\s*\((?:202[4-9]|203\d)\)|entry[\s-]level|internship|intern\b|student\b)', text))
        
        exp_match = re.search(r'(\d+[\+]?)\s*(?:to\s*\d+)?\s*(?:years?|yrs?)(?:\s+of)?\s+experience', text, re.IGNORECASE)
        if exp_match:
            try:
                est_years = float(exp_match.group(1).replace("+", ""))
            except ValueError:
                est_years = 0.5
        elif is_fresher:
            est_years = 0.5
        else:
            est_years = min(10.0, max(1.0, len(experience_items) * 1.5))

        candidate_domain = "Software & AI Engineering"
        if any(s in text_lower for s in ["sales", "quota", "account executive"]):
            candidate_domain = "Enterprise Sales & Business"

        return ParsedResume(
            contact=contact,
            summary=summary_text,
            skills=skills_list,
            experience=experience_items,
            projects=project_items,
            education=education_items,
            certifications=cert_items,
            links=list(set(all_links)),
            raw_text=text,
            page_count=page_count,
            candidate_domain=candidate_domain,
            estimated_experience_years=est_years,
            is_fresher_or_entry_level=is_fresher
        )

    @staticmethod
    def _extract_skills_from_text(text: str) -> List[str]:
        """Splits skills from bullet points, commas, pipelines, and tags."""
        skills = set()
        # Common skill keywords to look for deterministically
        common_tech = [
            "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust",
            "fastapi", "flask", "django", "spring boot", "react", "next.js", "vue", "angular", "node.js",
            "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "git", "linux", "terraform",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "sqlite",
            "machine learning", "deep learning", "nlp", "rag", "langchain", "crewai", "vector databases",
            "rest api", "graphql", "microservices", "sql", "nosql", "pandas", "numpy", "pytorch", "tensorflow"
        ]
        text_lower = text.lower()
        for tech in common_tech:
            # Match whole words/phrases
            if re.search(r'\b' + re.escape(tech) + r'\b', text_lower):
                skills.add(tech.title() if len(tech) > 3 else tech.upper())

        # Also parse bullets or comma separated items in the dedicated skills section
        for line in text.splitlines():
            clean = re.sub(r'^[-*•\d.]+\s*', '', line).strip()
            if "," in clean:
                for part in clean.split(","):
                    p = part.strip()
                    if 1 < len(p) < 30 and not any(skip in p.lower() for skip in ["experience", "summary", "university", "school"]):
                        skills.add(p)

        return sorted(list(skills))

resume_parser = ResumeParser()
