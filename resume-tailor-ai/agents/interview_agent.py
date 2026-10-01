"""
Interview Coach & Mock Interview Agent.
Generates multi-dimensional interview questions and evaluates candidate answers objectively.
"""
from typing import List, Dict, Any
from crewai import Agent
from llm.provider import llm_factory
from models.schemas import InterviewQuestion, MockInterviewEvaluation

def create_interview_agent() -> Agent:
    llm = llm_factory.get_crewai_llm(feature_name="interview_agent")
    return Agent(
        role="Senior Engineering Interview Coach & Evaluator",
        goal="Prepare candidates for grueling technical, system design, and behavioral interviews with actionable feedback.",
        backstory=(
            "You are a Bar Raiser and Senior Engineering Interviewer who has conducted hundreds of technical "
            "and architecture interviews at Tier-1 tech firms. You craft laser-targeted questions based on the candidate's "
            "actual projects and the target role requirements. You evaluate candidate responses objectively on technical "
            "correctness, conciseness, and clarity without subjective bias."
        ),
        verbose=False,
        llm=llm,
        allow_delegation=False
    )
