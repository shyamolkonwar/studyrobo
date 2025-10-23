import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "StudyRobo"

settings = Settings()