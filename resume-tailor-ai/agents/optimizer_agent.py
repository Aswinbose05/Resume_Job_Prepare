"""
Resume Optimizer Agent.
Generates tailored, high-impact resume enhancements strictly grounded in verified candidate facts.
"""
from crewai import Agent
from llm.provider import llm_factory

def create_optimizer_agent() -> Agent:
    llm = llm_factory.get_crewai_llm(feature_name="optimizer_agent")
    return Agent(
        role="Principal Resume Strategist & Career Optimizer",
        goal="Rewrite and optimize resume statements to highlight maximum engineering impact without fabricating unverified facts.",
        backstory=(
            "You are a prestigious Silicon Valley Engineering Career Coach and Editor. "
            "You transform passive bullet points into high-velocity STAR/XYZ-format engineering achievements. "
            "CRITICAL INTEGRITY DIRECTIVE: You never fabricate numbers, companies, or tools. You work strictly "
            "from the candidate's existing truthful experience, enhancing articulation, clarity, and keyword precision."
        ),
        verbose=False,
        llm=llm,
        allow_delegation=False
    )
