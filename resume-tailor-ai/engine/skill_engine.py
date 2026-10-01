"""
Skill Intelligence Engine.
Categorizes candidate skills into STRONG, PARTIAL, and MISSING.
Constructs targeted learning paths and strictly separates 'Safe to Highlight' from 'Skills to Learn'.
"""
from typing import List, Dict, Set, Any
from models.schemas import (
    ParsedResume, JobDescriptionData, SkillStatus, RecommendedSkill, SkillIntelligenceResult
)
from core.logger import logger

# Curated skill relationship graph & learning roadmap blueprints
SKILL_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "kubernetes": {
        "related": ["Docker", "Linux", "CI/CD", "AWS", "Cloud"],
        "roadmap": [
            "Containerization Fundamentals (Docker images, networks, volumes)",
            "Kubernetes Core Architecture (Control Plane, Worker Nodes, Kubelet)",
            "Basic Workloads (Pods, Deployments, ReplicaSets)",
            "Networking & Discovery (Services: ClusterIP, NodePort, Ingress)",
            "Config Management (ConfigMaps, Secrets, Volumes)",
            "Cloud Deployment (AWS EKS or GCP GKE with Helm Charts)"
        ]
    },
    "docker": {
        "related": ["Linux", "Git", "Python", "Backend"],
        "roadmap": [
            "Docker CLI & Architecture",
            "Writing Optimized Dockerfiles & Multi-stage builds",
            "Container Networking & Storage Volumes",
            "Multi-container Orchestration with Docker Compose",
            "Image Security Scanning & Publishing to Registry"
        ]
    },
    "aws": {
        "related": ["Cloud", "Linux", "Docker", "DevOps"],
        "roadmap": [
            "AWS Global Infrastructure & IAM Roles/Policies",
            "Compute Services (EC2, Lambda Serverless)",
            "Storage & Database (S3 Buckets, RDS PostgreSQL/MySQL)",
            "Networking (VPC, Subnets, Security Groups)",
            "Monitoring & Deployment (CloudWatch, ECS, ECR)"
        ]
    },
    "rag": {
        "related": ["Python", "Machine Learning", "LangChain", "Vector Databases", "LLM Integration"],
        "roadmap": [
            "Embeddings & Semantic Search Fundamentals",
            "Vector Database Ingestion & Indexing (ChromaDB / Pinecone)",
            "Document Chunking Strategies & Tokenization",
            "Retrieval Pipelines & Context Injection",
            "Reranking & Advanced RAG (Self-Query, HyDE, Multi-Query)",
            "RAG Triad Evaluation with TruLens or Ragas"
        ]
    },
    "crewai": {
        "related": ["Python", "LangChain", "AI Agents", "LLM Integration"],
        "roadmap": [
            "Multi-Agent AI Systems Theory & Role-Playing Agents",
            "CrewAI Core: Agents, Tasks, Tools, and Crews",
            "Tool Integration (Custom Tools, Serper, Scraping)",
            "Hierarchical Process vs Sequential Execution",
            "Memory Management & Agent Collaboration Patterns"
        ]
    },
    "fastapi": {
        "related": ["Python", "REST API", "Pydantic", "Backend"],
        "roadmap": [
            "Type hints, Async/Await concurrency model",
            "Routing, Path & Query Parameters, Request Bodies",
            "Pydantic V2 Data Validation and Serialization",
            "Dependency Injection System & Authentication (JWT)",
            "Middleware, Background Tasks, and Database Integration (SQLAlchemy/Tortoise)",
            "Dockerizing and Deploying with Uvicorn"
        ]
    },
    "spring boot": {
        "related": ["Java", "OOP", "MySQL", "REST API"],
        "roadmap": [
            "Spring Core Concepts: IoC Container & Dependency Injection",
            "Building RESTful Web Services with @RestController",
            "Data Persistence with Spring Data JPA & Hibernate",
            "Application Security with Spring Security & JWT",
            "Testing with JUnit 5 and Mockito",
            "Production Deployment with Spring Boot Actuator & Docker"
        ]
    },
    "ci/cd": {
        "related": ["Git", "Linux", "Docker", "GitHub Actions"],
        "roadmap": [
            "Git Workflow & Branching Strategies",
            "Automated Testing Pipelines",
            "GitHub Actions: Workflows, Jobs, Steps, and Secrets",
            "Building & Pushing Docker Images to Container Registries",
            "Automated Staging and Production Deployments"
        ]
    }
}

class SkillIntelligenceEngine:
    """Evaluates candidate skill posture and generates structured gap analyses."""

    @classmethod
    def analyze(cls, resume: ParsedResume, jd: JobDescriptionData) -> SkillIntelligenceResult:
        """
        Extracts existing skills, identifies STRONG, PARTIAL, and MISSING skills,
        and generates safe recommendations.
        """
        resume_skills_lower = {s.lower() for s in resume.skills}
        resume_text_lower = resume.raw_text.lower()
        
        strong_skills = []
        partial_skills = []
        missing_skills = []
        skill_breakdown = []
        skills_to_learn = []
        skills_safe_to_highlight = []

        # Find which candidate skills are present and strongly backed by projects
        for skill in resume.skills:
            s_lower = skill.lower()
            # If skill is explicitly mentioned in projects or experience, it is Strong
            is_in_projects = any(s_lower in str(p).lower() for p in resume.projects)
            is_in_exp = any(s_lower in str(e).lower() for e in resume.experience)
            if is_in_projects or is_in_exp or len(resume.projects) > 0:
                strong_skills.append(skill)
                skills_safe_to_highlight.append(skill)

        # Evaluate skills required by the target job description
        for jd_skill in jd.required_skills:
            jd_skill_lower = jd_skill.lower()
            
            # 1. Check if candidate already has this skill
            has_direct = (jd_skill_lower in resume_skills_lower) or (jd_skill_lower in resume_text_lower)

            tax_entry = SKILL_TAXONOMY.get(jd_skill_lower)
            related_found = []
            if tax_entry:
                for rel in tax_entry["related"]:
                    if rel.lower() in resume_skills_lower or rel.lower() in resume_text_lower:
                        related_found.append(rel)

            if has_direct:
                status = SkillStatus.STRONG
                importance = "High"
                reason = "Directly required by the target role and confirmed in your profile."
                learning_path = ["Skill verified in resume - review advanced production scenarios for technical interviews."]
                if jd_skill not in strong_skills:
                    strong_skills.append(jd_skill)
            elif related_found:
                status = SkillStatus.PARTIAL
                importance = "High"
                reason = f"Required by JD. You possess strong foundational skills ({', '.join(related_found)}), making this a fast ramp-up."
                learning_path = tax_entry["roadmap"] if tax_entry else [
                    f"Review {jd_skill} core architecture",
                    f"Leverage your knowledge of {related_found[0]} to build a proof-of-concept",
                    "Add a GitHub project demonstrating end-to-end integration"
                ]
                partial_skills.append(jd_skill)
                skills_to_learn.append(jd_skill)
            else:
                status = SkillStatus.MISSING
                importance = "High" if len(missing_skills) < 3 else "Medium"
                reason = "Required or preferred by the job description but not detected in your resume evidence."
                learning_path = tax_entry["roadmap"] if tax_entry else [
                    f"Study official {jd_skill} documentation and core fundamentals",
                    "Complete a hands-on project solving a real-world problem",
                    "Publish repository with clean documentation before listing on resume"
                ]
                missing_skills.append(jd_skill)
                skills_to_learn.append(jd_skill)

            skill_breakdown.append(RecommendedSkill(
                skill=jd_skill,
                status=status,
                importance=importance,
                reason=reason,
                existing_related_skills=related_found,
                recommended_learning_path=learning_path
            ))

        return SkillIntelligenceResult(
            existing_skills=resume.skills,
            strong_skills=sorted(list(set(strong_skills))),
            partial_skills=sorted(list(set(partial_skills))),
            missing_skills=sorted(list(set(missing_skills))),
            skill_breakdown=skill_breakdown,
            skills_safe_to_highlight=sorted(list(set(skills_safe_to_highlight))),
            skills_to_learn=sorted(list(set(skills_to_learn)))
        )

skill_engine = SkillIntelligenceEngine()
