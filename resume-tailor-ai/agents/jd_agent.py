"""
Job Description & Market Intelligence Agent.
Extracts hard and soft requirements, domain expectations, and qualification thresholds.
"""
from typing import List
from crewai import Agent
from llm.provider import llm_factory
from core.config import settings

def create_jd_agent() -> Agent:
    llm = llm_factory.get_crewai_llm(feature_name="jd_agent")
    tools = []
    
    # Optional Serper live web search
    if settings.SERPER_API_KEY and not settings.SERPER_API_KEY.startswith("your_"):
        try:
            from crewai_tools import SerperDevTool
            tools.append(SerperDevTool())
        except Exception:
            pass

    return Agent(
        role="Tech Job Market & Role Specialist",
        goal="Deconstruct job postings into precise technical skills, seniority requirements, and core engineering expectations.",
        backstory=(
            "You are an expert Hiring Manager and Technical Sourcer for top tech companies. "
            "You understand the difference between core architectural necessities and superficial buzzwords. "
            "You distill job descriptions into crystal-clear engineering requirements."
        ),
        tools=tools,
        verbose=False,
        llm=llm,
        allow_delegation=False
    )
