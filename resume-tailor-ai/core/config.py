"""
Configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Info
    APP_NAME: str = "AI Resume Analyzer & Job Preparation System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Primary & Fallback LLM Provider Settings
    # Options: gemini | groq | openrouter | portkey
    LLM_PROVIDER: str = Field(default="gemini", description="Primary LLM provider")
    FALLBACK_PROVIDER: str = Field(default="groq", description="Fallback LLM provider")
    
    # Model names
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"

    # API Keys
    GEMINI_API_KEY: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    # Portkey AI Gateway
    PORTKEY_API_KEY: Optional[str] = None
    PORTKEY_VIRTUAL_KEY: Optional[str] = None
    PORTKEY_CONFIG_ID: Optional[str] = None
    PORTKEY_TRACE_ID: Optional[str] = None

    # LangSmith Observability & Tracing
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "ai-career-intelligence"

    # Security Controls
    ENABLE_PROMPT_GUARD: bool = True
    ENABLE_SSRF_PROTECTION: bool = True
    ENABLE_PII_MASKING: bool = True
    ENABLE_RATE_LIMITING: bool = True

    # Rate Limiting (Token Bucket / Window)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 15
    RATE_LIMIT_BURST: int = 25

    # File Upload Limits
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_RESUME_PAGES: int = 15
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "md", "txt"]

    # Allowed Outbound URL Schemes and Domains
    ALLOWED_URL_SCHEMES: List[str] = ["http", "https"]
    BLOCKED_HOSTNAMES: List[str] = [
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254", "metadata.google.internal"
    ]

    # Module 2: RAG Assistant & Vector Database Settings
    EMBEDDING_PROVIDER: str = "chroma_onnx"  # Free local ONNX embedding
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 4
    ALLOWED_RAG_EXTENSIONS: List[str] = ["pdf", "docx", "txt", "md", "csv"]


settings = Settings()
