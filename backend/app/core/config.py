import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # "openai", "glm", "gemini", "mistral", or "openrouter"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GLM_API_KEY: str = os.getenv("GLM_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Model Names (configurable)
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    GLM_MODEL: str = os.getenv("GLM_MODEL", "glm-4.5")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "StudyRobo"

    # Supabase configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Google OAuth (now handled by Supabase, but keeping for reference)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

settings = Settings()
