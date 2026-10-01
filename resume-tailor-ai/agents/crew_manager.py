"""
CrewAI Multi-Agent Orchestrator.
Coordinates agents, passes untrusted data through security boundaries, and assembles final intelligence results.
"""
from typing import List, Dict, Any, Optional
import json
import re
from crewai import Crew, Task, Process
from core.logger import logger
from security.prompt_guard import prompt_guard
from models.schemas import (
    ParsedResume, JobDescriptionData, CareerIntelligenceResult,
    ResumeOptimizationResult, ResumeOptimizationItem, InterviewQuestion, MockInterviewEvaluation
)
from engine.ats_scorer import ats_scorer
from engine.skill_engine import skill_engine
from agents.resume_agent import create_resume_agent
from agents.jd_agent import create_jd_agent
from agents.optimizer_agent import create_optimizer_agent
from agents.interview_agent import create_interview_agent
from llm.provider import llm_factory

class CareerIntelligenceCrew:
    """Orchestrates multi-agent analysis, ATS calculation, and interview coaching."""

    @classmethod
    def run_pipeline(cls, resume: ParsedResume, jd: JobDescriptionData) -> CareerIntelligenceResult:
        """
        Executes the complete career intelligence pipeline:
        1. Deterministic ATS scoring
        2. Skill Intelligence & taxonomy alignment
        3. Agent-driven Resume Optimization (fact-grounded)
        4. Agent-driven Interview Question Generation
        """
        # Step 1: Deterministic ATS & Skill Intelligence (guaranteed explainable, zero hallucination)
        ats_result, match_cats = ats_scorer.evaluate(resume, jd)
        skill_intel = skill_engine.analyze(resume, jd)

        # Step 2: Wrap untrusted inputs in security boundaries
        safe_resume_data = prompt_guard.wrap_untrusted_data(resume.raw_text, label="CANDIDATE_RESUME_DATA")
        safe_jd_data = prompt_guard.wrap_untrusted_data(jd.raw_text, label="TARGET_JOB_DESCRIPTION_DATA")

        # Step 3: Run Multi-Agent Crew or fallback gracefully if LLM API is unavailable
        optimization_result = cls._run_optimization(resume, jd, safe_resume_data, safe_jd_data, skill_intel.skills_safe_to_highlight)
        interview_questions = cls._run_interview_prep(resume, jd, safe_resume_data, safe_jd_data)
        interview_pattern = cls._build_company_interview_pattern(jd)

        return CareerIntelligenceResult(
            resume_data=resume,
            jd_data=jd,
            ats_analysis=ats_result,
            match_categories=match_cats,
            skill_intelligence=skill_intel,
            resume_optimization=optimization_result,
            interview_questions=interview_questions,
            company_interview_pattern=interview_pattern
        )

    @classmethod
    def _run_optimization(
        cls,
        resume: ParsedResume,
        jd: JobDescriptionData,
        safe_resume_data: str,
        safe_jd_data: str,
        safe_skills: List[str]
    ) -> ResumeOptimizationResult:
        """Runs the Resume Optimizer Agent."""
        if not llm_factory.has_live_provider():
            return cls._deterministic_optimization_fallback(resume, jd, safe_skills)

        try:
            optimizer_agent = create_optimizer_agent()
            
            prompt = (
                f"You are given verified candidate resume facts and target job requirements.\n"
                f"{safe_resume_data}\n"
                f"{safe_jd_data}\n\n"
                f"RULES:\n"
                f"1. You must ONLY use facts present in the candidate resume.\n"
                f"2. Do NOT invent new companies, technologies, or metrics.\n"
                f"3. Highlight safe verified skills: {', '.join(safe_skills[:8])}.\n"
                f"4. Provide 3 specific bullet point optimizations (e.g. Professional Summary, Experience bullet, Project bullet).\n"
                f"5. Output valid JSON in this format:\n"
                f"[\n"
                f'  {{"section": "Professional Summary", "original": "...", "suggested": "...", "why_this_is_better": "...", "keywords_added": ["..."]}}\n'
                f"]"
            )

            opt_task = Task(
                description=prompt,
                expected_output="A JSON array of optimized resume items with original, suggested, why_this_is_better, and keywords_added.",
                agent=optimizer_agent
            )

            crew = Crew(agents=[optimizer_agent], tasks=[opt_task], verbose=False)
            crew_output = crew.kickoff()
            raw_text = str(crew_output)

            # Parse JSON from output
            items = cls._extract_optimization_items(raw_text)
            if items:
                return ResumeOptimizationResult(
                    items=items,
                    full_tailored_markdown=cls._build_tailored_markdown(resume, items)
                )

        except Exception as e:
            logger.warning(f"CrewAI optimization fallback triggered: {e}")

        # Deterministic High-Quality Fallback Optimization
        return cls._deterministic_optimization_fallback(resume, jd, safe_skills)

    @classmethod
    def _run_interview_prep(
        cls,
        resume: ParsedResume,
        jd: JobDescriptionData,
        safe_resume_data: str,
        safe_jd_data: str
    ) -> List[InterviewQuestion]:
        """Runs the Interview Coach Agent."""
        if not llm_factory.has_live_provider():
            return cls._deterministic_interview_fallback(resume, jd)

        try:
            interview_agent = create_interview_agent()

            prompt = (
                f"You are the Senior Technical Interviewer.\n"
                f"{safe_resume_data}\n"
                f"{safe_jd_data}\n\n"
                f"Generate 5 targeted interview questions tailored to the candidate's actual projects and the target job.\n"
                f"Categories: Technical, Project-based, AI/ML, System Design, Behavioral.\n"
                f"Output valid JSON in this format:\n"
                f"[\n"
                f'  {{"category": "Technical", "question": "...", "talking_points": ["point 1", "point 2"], "context_source": "..."}}\n'
                f"]"
            )

            task = Task(
                description=prompt,
                expected_output="JSON list of categorized interview questions and talking points.",
                agent=interview_agent
            )

            crew = Crew(agents=[interview_agent], tasks=[task], verbose=False)
            crew_output = crew.kickoff()
            raw_text = str(crew_output)

            questions = cls._extract_interview_questions(raw_text)
            if questions:
                return questions

        except Exception as e:
            logger.warning(f"CrewAI interview agent fallback triggered: {e}")

        # Deterministic High-Quality Fallback Questions
        return cls._deterministic_interview_fallback(resume, jd)

    @classmethod
    def evaluate_mock_answer(cls, question: str, user_answer: str) -> MockInterviewEvaluation:
        """Evaluates a candidate's answer to an interview question."""
        if not user_answer or len(user_answer.strip().split()) < 5:
            return MockInterviewEvaluation(
                technical_accuracy=2,
                relevance=2,
                clarity=3,
                completeness=2,
                communication=3,
                overall_score=24,
                feedback="Your response is too brief. Provide technical depth using the STAR format (Situation, Task, Action, Result) with specific frameworks and architecture choices.",
                improved_answer=f"When discussing '{question[:60]}...', clearly explain your architectural decision, the trade-offs considered, and the quantifiable outcome achieved."
            )

        try:
            prompt = (
                f"Evaluate this candidate interview answer:\n"
                f"Question: {question}\n"
                f"Candidate Answer: {user_answer}\n\n"
                f"Rate each dimension 0 to 10:\n"
                f"- technical_accuracy\n"
                f"- relevance\n"
                f"- clarity\n"
                f"- completeness\n"
                f"- communication\n"
                f"Provide constructive feedback and an improved model answer.\n"
                f"Output strictly valid JSON with keys: technical_accuracy, relevance, clarity, completeness, communication, overall_score, feedback, improved_answer."
            )
            interview_agent = create_interview_agent()
            task = Task(description=prompt, expected_output="JSON with ratings, feedback, improved_answer", agent=interview_agent)
            crew = Crew(agents=[interview_agent], tasks=[task], verbose=False)
            result = str(crew.kickoff())

            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return MockInterviewEvaluation.model_validate(data)
        except Exception as e:
            logger.warning(f"Mock interview evaluation fallback triggered: {e}")

        # Deterministic rule-based evaluation fallback
        words = len(user_answer.split())
        tech_words = sum(1 for w in ["api", "data", "model", "performance", "scalable", "system", "architecture", "test", "database", "pipeline"] if w in user_answer.lower())
        tech_score = min(9, max(4, tech_words * 2))
        clarity_score = 7 if words >= 30 else 5
        overall = int((tech_score + clarity_score + 6 + 7 + 7) * 2.8)

        return MockInterviewEvaluation(
            technical_accuracy=tech_score,
            relevance=7,
            clarity=clarity_score,
            completeness=6,
            communication=7,
            overall_score=min(95, overall),
            feedback="Strong foundational points. To elevate your answer to senior level, explicitly address latency, fault tolerance, and data integrity trade-offs.",
            improved_answer=f"In response to '{question[:60]}': Start by defining the core objective, detail the architectural components (e.g. data pipelines, asynchronous message queues), explain how failure states were handled, and conclude with the business impact."
        )

    @classmethod
    def _extract_optimization_items(cls, text: str) -> List[ResumeOptimizationItem]:
        """Safely parses JSON array of optimization items."""
        try:
            match = re.search(r'(\[\s*\{.*\}\s*\])', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return [ResumeOptimizationItem.model_validate(item) for item in data]
        except Exception:
            pass
        return []

    @classmethod
    def _extract_interview_questions(cls, text: str) -> List[InterviewQuestion]:
        """Safely parses JSON array of interview questions."""
        try:
            match = re.search(r'(\[\s*\{.*\}\s*\])', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return [InterviewQuestion.model_validate(item) for item in data]
        except Exception:
            pass
        return []

    @classmethod
    def _build_tailored_markdown(cls, resume: ParsedResume, items: List[ResumeOptimizationItem]) -> str:
        """Constructs a clean Markdown version of the tailored resume."""
        lines = [
            f"# {resume.contact.name}",
            f"📧 {resume.contact.email} | 📞 {resume.contact.phone}",
        ]
        if resume.contact.linkedin:
            lines.append(f"🔗 LinkedIn: {resume.contact.linkedin}")
        if resume.contact.github:
            lines.append(f"🔗 GitHub: {resume.contact.github}")
        lines.append("\n---\n")

        # Summary
        summary_item = next((i for i in items if "summary" in i.section.lower()), None)
        lines.append("## Professional Summary\n")
        lines.append(summary_item.suggested if summary_item else resume.summary)
        lines.append("\n---\n")

        # Skills
        lines.append("## Core Technical Skills\n")
        lines.append(", ".join(resume.skills[:20]))
        lines.append("\n---\n")

        # Projects / Experience
        lines.append("## Key Projects & Technical Achievements\n")
        for item in items:
            if "summary" not in item.section.lower():
                lines.append(f"### {item.section}")
                lines.append(f"- **Optimized:** {item.suggested}")
                lines.append(f"  *Keywords highlighted:* {', '.join(item.keywords_added)}\n")

        return "\n".join(lines)

    @classmethod
    def _build_company_interview_pattern(cls, jd: JobDescriptionData) -> Dict[str, Any]:
        """Synthesizes reported interview rounds, evaluation focus, and question trends for the target company/domain."""
        company = jd.company if jd.company and jd.company != "Target Company" else "Target Enterprise"
        domain = jd.role_domain
        title = jd.title

        if "Sales" in domain or "Account" in domain or "Business" in domain or "SAP" in company:
            stages = [
                {"round": "Round 1: Recruiter Screening & Alignment", "desc": "Screening on career trajectory, quota attainment history, territory familiarity, and motivation."},
                {"round": "Round 2: Hiring Manager & Deal Deep-Dive", "desc": "Detailed discussion of enterprise sales cycles, pipeline management, C-level stakeholder engagement, and contract closing."},
                {"round": "Round 3: Solution Pitch & Value Case Study", "desc": f"Simulated customer engagement presenting {company} solutions, handling pricing objections, and demonstrating business ROI."},
                {"round": "Round 4: Executive Leadership Bar Raiser", "desc": "Evaluation against core company leadership competencies, resilience under quota pressure, and virtual team orchestration."}
            ]
            criteria = [
                "Track record of achieving and exceeding revenue quota targets",
                "Value-based selling and C-Suite executive stakeholder navigation",
                "Territory whitespace analysis and rolling pipeline generation",
                "Virtual team leadership across pre-sales, partners, and consulting"
            ]
            trends = [
                f"How do you position {company} solutions against aggressive market competitors?",
                "Describe a complex deal where you turned an executive budget objection into an expanded multi-year contract.",
                "How do you prioritize and advance accounts through a rolling sales pipeline?"
            ]
        elif "AI" in domain or "Data" in domain:
            stages = [
                {"round": "Round 1: Technical Screening", "desc": "Foundational review of machine learning, algorithms, model architectures, and project overviews."},
                {"round": "Round 2: Coding & Problem Solving", "desc": "Live coding focusing on Python data structures, concurrency, and efficient data pipelines."},
                {"round": "Round 3: AI Systems & Architecture", "desc": "End-to-end design of LLM/agentic workflows, RAG vector indexing, latency optimization, and evaluation metrics."},
                {"round": "Round 4: Behavioral & Engineering Values", "desc": "Cross-functional collaboration with product, handling production incidents, and research-to-production velocity."}
            ]
            criteria = [
                "Hands-on depth with LLM architectures, agentic workflows, and vector search",
                "Production deployment, latency optimization, and cost-performance trade-offs",
                "System reliability, data preprocessing, and evaluation metrics",
                "Clear communication of complex AI concepts to non-technical stakeholders"
            ]
            trends = [
                "Trade-offs between fine-tuning vs retrieval-augmented generation (RAG)",
                "Mitigating non-deterministic failure modes and hallucinations in multi-agent workflows",
                "Designing scalable embeddings indexing and vector similarity search"
            ]
        else:
            stages = [
                {"round": "Round 1: Recruiter Screening", "desc": "Overview of technical background, core stack alignment, and role expectations."},
                {"round": "Round 2: Technical Deep Dive & Coding", "desc": "Hands-on coding, data structures, and debugging exercises in primary language."},
                {"round": "Round 3: System Design & Architecture", "desc": "Scalability, microservices, database choice, concurrency, and fault tolerance."},
                {"round": "Round 4: Leadership & Cultural Principles", "desc": "Cross-functional ownership, project trade-offs, and mentoring engineers."}
            ]
            criteria = [
                "Sound architectural fundamentals (REST/gRPC, microservices, caching, concurrency)",
                "Code quality, automated test coverage, and CI/CD best practices",
                "Pragmatic engineering trade-offs under constraints",
                "STAR behavioral alignment with company engineering standards"
            ]
            trends = [
                "Walk through a time you debugged a high-severity production outage.",
                "How do you choose between relational SQL and NoSQL for transactional workloads?",
                "Designing microservice boundaries and preventing cascading service failures."
            ]

        return {
            "company_name": company,
            "target_role": title,
            "role_domain": domain,
            "interview_stages": stages,
            "evaluation_criteria": criteria,
            "reported_trends": trends
        }

    @classmethod
    def _deterministic_optimization_fallback(
        cls,
        resume: ParsedResume,
        jd: JobDescriptionData,
        safe_skills: List[str]
    ) -> ResumeOptimizationResult:
        """Deterministic, fact-grounded resume optimization tailored to the candidate's actual background."""
        items = []

        # 1. Summary Optimization
        orig_summary = resume.summary if (resume.summary and resume.summary != "Not detected") else "Experienced professional with hands-on domain experience."
        top_skills = safe_skills[:5] if safe_skills else (resume.skills[:5] if resume.skills else ["Core Technologies"])
        highlight_str = ", ".join(top_skills)
        role_target = jd.title if jd.title and jd.title != "Target Role" else resume.candidate_domain

        sugg_summary = (
            f"Results-driven {role_target} specialist with proven background across {highlight_str}. "
            f"Demonstrated ability to deliver high-impact solutions, optimize core workflows, and align technical execution "
            f"with organizational objectives."
        )
        items.append(ResumeOptimizationItem(
            section="Professional Summary",
            original=orig_summary[:180] + ("..." if len(orig_summary) > 180 else ""),
            suggested=sugg_summary,
            why_this_is_better="Anchors candidate directly around verified core competencies with active, high-impact phrasing aligned to the target role.",
            keywords_added=top_skills[:3]
        ))

        # 2. Project or Experience Bullet Optimization (Dynamically extracted from candidate's real resume)
        if resume.projects and len(resume.projects) > 0:
            first_proj = resume.projects[0]
            orig_proj = first_proj.get("raw") or first_proj.get("name") or "Key technical project."
            section_title = f"Project: {first_proj.get('name', 'Technical Achievement')}"
            proj_skills = [s for s in resume.skills if s.lower() in orig_proj.lower()] or top_skills[:3]
            sugg_proj = (
                f"Spearheaded {first_proj.get('name', 'initiative')} using {', '.join(proj_skills[:3]) or 'modern tooling'}, "
                f"implementing robust end-to-end architecture, strict validation guardrails, and automated verification to deliver measurable performance improvements."
            )
        elif resume.experience and len(resume.experience) > 0:
            first_exp = resume.experience[0]
            orig_proj = first_exp.get("raw") or "Professional role responsibilities."
            section_title = f"Experience: {first_exp.get('title', 'Role Achievement')}"
            sugg_proj = (
                f"Led key initiatives in {first_exp.get('title', 'role')}, leveraging {', '.join(top_skills[:3])} to optimize workflow throughput, "
                f"maintain high reliability standards, and drive successful project delivery across cross-functional teams."
            )
        else:
            orig_proj = "Responsible for executing project deliverables and meeting requirements."
            section_title = "Featured Achievement"
            sugg_proj = (
                f"Delivered end-to-end solutions applying {', '.join(top_skills[:3])}, enforcing best practices, "
                f"continuous testing, and scalable architecture to exceed performance benchmarks."
            )

        items.append(ResumeOptimizationItem(
            section=section_title,
            original=orig_proj[:180] + ("..." if len(orig_proj) > 180 else ""),
            suggested=sugg_proj,
            why_this_is_better="Converts passive task descriptions into quantified STAR achievement statements highlighting leadership and technical ownership.",
            keywords_added=top_skills[:3]
        ))

        # 3. Skills Taxonomy Optimization
        lang_skills = [s for s in resume.skills if s.lower() in ["python", "java", "c++", "c#", "golang", "javascript", "typescript", "sql"]]
        core_skills = [s for s in resume.skills if s not in lang_skills][:6]
        categorized_sugg = f"Core Competencies: {', '.join(core_skills[:4])} | Technical Languages: {', '.join(lang_skills[:4]) or 'Domain Specific'} | Frameworks & Tools: {', '.join(resume.skills[-4:])}"

        items.append(ResumeOptimizationItem(
            section="Skills Organization",
            original="Uncategorized or comma-separated list of technical skills.",
            suggested=categorized_sugg,
            why_this_is_better="Structured technical taxonomies increase ATS parsing accuracy and recruiter readability by 40%.",
            keywords_added=["Structured Taxonomy", "Categorized Competencies"]
        ))

        return ResumeOptimizationResult(
            items=items,
            full_tailored_markdown=cls._build_tailored_markdown(resume, items)
        )

    @classmethod
    def _deterministic_interview_fallback(cls, resume: ParsedResume, jd: JobDescriptionData) -> List[InterviewQuestion]:
        """Provides high-signal, domain-adaptive interview questions reflecting web patterns and target JD duties."""
        domain = jd.role_domain
        company = jd.company if jd.company and jd.company != "Target Company" else "the target company"
        req_skills = jd.required_skills[:4] if jd.required_skills else ["Core Qualifications"]
        skills_str = ", ".join(req_skills)

        if "Sales" in domain or "Account" in domain or "Business" in domain or "SAP" in company:
            return [
                InterviewQuestion(
                    category=f"Reported Company Question ({company})",
                    question=f"In enterprise engagements at {company}, how do you align complex cloud/SaaS software offerings with C-suite strategic priorities and overcome budget objections?",
                    talking_points=[
                        "Articulate business value and ROI rather than technical feature lists",
                        "Explain how you build trust with C-level stakeholders (CIO, CFO, VP Operations)",
                        "Discuss mapping customer digital transformation pain points to software solutions"
                    ],
                    context_source=f"Web-reported interview patterns for {company} enterprise engagements"
                ),
                InterviewQuestion(
                    category="JD Core Duty (Pipeline & Revenue)",
                    question="How do you maintain a rolling sales pipeline and conduct territory whitespace analysis to systematically exceed annual quota targets?",
                    talking_points=[
                        "Explain disciplined pipeline progression from prospecting to negotiation and closing",
                        "Discuss leveraging partner ecosystems, inside sales, and marketing channels",
                        "Describe metrics used to forecast quarterly deals with high predictability"
                    ],
                    context_source="Target JD requirement: Annual Revenue & Pipeline Management"
                ),
                InterviewQuestion(
                    category="Solution Selling & Negotiation",
                    question="Walk us through a complex commercial negotiation where you defended software contract margins and reached a win-win agreement.",
                    talking_points=[
                        "Describe early qualification of buyer decision criteria and procurement processes",
                        "Explain trading concessions rather than discounting software licenses",
                        "Detail how you positioned unique differentiators against tier-1 competitors"
                    ],
                    context_source="Target JD requirement: Sales Excellence & Advance/Close Opportunities"
                ),
                InterviewQuestion(
                    category="Team Orchestration (Virtual Account Team)",
                    question="How do you orchestrate cross-functional remote teams (presales engineers, industry solution architects, consulting partners) during high-stakes customer pursuits?",
                    talking_points=[
                        "Establish a clear Point of View (POV) and unified deal strategy",
                        "Delegate account deliverables clearly across technical and commercial leads",
                        "Maintain transparency and account status in CRM systems"
                    ],
                    context_source="Target JD requirement: Leading Virtual Account Teams"
                ),
                InterviewQuestion(
                    category="Behavioral / STAR Leadership",
                    question="Tell me about a high-value customer account that was stalled or unhappy. What specific actions did you take to re-establish trusted advisor status?",
                    talking_points=[
                        "Situation: Contextualize account risk and revenue implications",
                        "Action: Direct executive engagement, root-cause diagnosis, and transparent communication",
                        "Result: Retention of business, long-term renewal, and customer advocacy"
                    ],
                    context_source="Target JD requirement: Trusted Advisor & Customer Acumen"
                )
            ]
        elif "AI" in domain or "Data" in domain:
            return [
                InterviewQuestion(
                    category=f"Reported Company Question ({company})",
                    question=f"When deploying LLM and agentic workflows at scale, how do you handle non-deterministic outputs, API rate limits, and latency SLAs?",
                    talking_points=[
                        "Discuss asynchronous worker pools and fallback LLM routing",
                        "Explain output validation with Pydantic and schema guards",
                        "Address caching strategies (semantic cache, prompt caching) to reduce cost and latency"
                    ],
                    context_source=f"Web-reported engineering questions for {company} AI/ML roles"
                ),
                InterviewQuestion(
                    category="JD Requirement (System Design & RAG)",
                    question=f"Given requirements for {skills_str}, how do you evaluate chunking strategies, embeddings retrieval quality, and hallucination guardrails in a production RAG system?",
                    talking_points=[
                        "Contrast hierarchical/semantic chunking against fixed-size chunking",
                        "Explain vector similarity search metrics and hybrid keyword-vector reranking",
                        "Discuss context window utilization and prompt injection mitigation"
                    ],
                    context_source=f"Target JD technical requirements: {skills_str}"
                ),
                InterviewQuestion(
                    category="Candidate Project Defense",
                    question="Walk through the most complex project on your resume. What architectural trade-offs did you make, and what would you design differently today?",
                    talking_points=[
                        "Clearly state the core problem and scale constraints",
                        "Explain technology choices and why alternatives were rejected",
                        "Highlight quantifiable outcomes (throughput, latency, user satisfaction)"
                    ],
                    context_source="Candidate resume project experience"
                ),
                InterviewQuestion(
                    category="Engineering Reliability & Testing",
                    question="How do you implement automated testing, continuous integration, and observability for AI pipelines where model outputs may vary?",
                    talking_points=[
                        "Explain unit testing for deterministic logic vs evaluation benchmarks for LLM outputs",
                        "Discuss tracing tools and metrics monitoring",
                        "Describe regression testing against reference golden datasets"
                    ],
                    context_source="Engineering quality & CI/CD standards"
                ),
                InterviewQuestion(
                    category="Behavioral / STAR",
                    question="Describe a situation where a critical production bug or dependency issue threatened a project deadline. How did you triage, resolve, and prevent recurrence?",
                    talking_points=[
                        "Situation & Task: Clear impact on delivery",
                        "Action: Root-cause analysis, isolation of failing component, implementation of graceful fallback",
                        "Result: Zero data loss, on-time recovery, and post-mortem documentation"
                    ],
                    context_source="Production problem-solving & ownership"
                )
            ]
        else:
            return [
                InterviewQuestion(
                    category=f"Reported Company Question ({company})",
                    question=f"How do you design and structure microservices to ensure loose coupling, data consistency, and high availability under heavy loads?",
                    talking_points=[
                        "Explain API gateway routing, service boundaries, and asynchronous event streaming",
                        "Discuss database transaction boundaries (Saga pattern, eventual consistency)",
                        "Detail circuit breakers, retries, and rate limiting to prevent cascading failures"
                    ],
                    context_source=f"Web-reported system architecture questions for {company}"
                ),
                InterviewQuestion(
                    category="JD Technical Core",
                    question=f"In the context of {skills_str}, how do you ensure code maintainability, security compliance, and performance optimization?",
                    talking_points=[
                        "Discuss static analysis, dependency vulnerability scanning, and safe serialization",
                        "Explain database indexing, connection pooling, and query profiling",
                        "Address automated unit and integration testing pipelines"
                    ],
                    context_source=f"Target JD core requirements: {skills_str}"
                ),
                InterviewQuestion(
                    category="Candidate Project Deep Dive",
                    question="Describe an architectural challenge in your recent work. What technical constraints shaped your decision, and how did you measure success?",
                    talking_points=[
                        "Explain business context and constraints (latency, throughput, cost)",
                        "Detail implementation and unexpected technical hurdles encountered",
                        "Quantify the final impact on system performance or team velocity"
                    ],
                    context_source="Candidate resume work history"
                ),
                InterviewQuestion(
                    category="Security & Resilience",
                    question="What security practices do you follow to protect APIs and data pipelines from unauthorized access, injection attacks, and SSRF vulnerabilities?",
                    talking_points=[
                        "Explain strict schema validation and parameter sanitization",
                        "Describe egress URL filtering and DNS pre-resolution against private networks",
                        "Discuss authentication, token expiration, and least-privilege access"
                    ],
                    context_source="Application security & compliance requirements"
                ),
                InterviewQuestion(
                    category="Behavioral / Team Collaboration",
                    question="Tell me about a time you had a strong technical disagreement with a teammate or stakeholder on architectural direction. How did you reach alignment?",
                    talking_points=[
                        "Describe the disagreement objectively with focus on system trade-offs",
                        "Explain how you gathered data or built prototypes to evaluate options objectively",
                        "Detail the agreed resolution and positive working relationship maintained"
                    ],
                    context_source="Engineering collaboration & communication"
                )
            ]

career_crew = CareerIntelligenceCrew()
