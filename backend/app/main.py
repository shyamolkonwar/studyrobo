import logging
import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

# Configure logging to suppress unwanted logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Suppress pypdf cryptography warning
warnings.filterwarnings("ignore", message="ARC4 has been moved")

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s:     %(message)s')

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
        "https://satro.space",
        "https://backend.satro.space"
    ],  # Allow local development, Docker service, and production domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "StudyRobo API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
