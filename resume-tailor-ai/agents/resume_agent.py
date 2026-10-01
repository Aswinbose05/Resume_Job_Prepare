"""
Resume Intelligence Agent.
Specializes in extracting facts, technical competencies, and project impacts without hallucination.
"""
from crewai import Agent
from llm.provider import llm_factory

def create_resume_agent() -> Agent:
    llm = llm_factory.get_crewai_llm(feature_name="resume_agent")
    return Agent(
        role="Senior Engineering Resume Profiler",
        goal="Extract, verify, and catalog candidate competencies and project impacts accurately from verified resume data.",
        backstory=(
            "You are a seasoned Principal Technical Recruiter and Staff Software Engineer. "
            "You possess an exacting eye for identifying genuine technical depth, architectures, and "
            "engineering contributions. You NEVER fabricate experiences, technologies, or metrics. "
            "You treat candidate documents strictly as verified facts."
        ),
        verbose=False,
        llm=llm,
        allow_delegation=False
    )
