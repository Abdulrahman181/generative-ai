"""Application configuration via environment variables with safe defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

                                                                                
SQLALCHEMY_DATABASE_URL: str = os.getenv(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'resume_analyzer.db'}"
)

                                                                                
def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is required. Set it in the deployment environment or a local .env file."
        )
    if value.lower().startswith("replace-with-"):
        raise RuntimeError(f"{name} still contains the placeholder from .env.example.")
    return value


SECRET_KEY: str = _required_env("SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters long.")
ALGORITHM: str = "HS256"
try:
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
except ValueError as exc:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer.") from exc
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer.")

                                                                                
UPLOAD_DIR: Path = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

                                                                                
MIN_PASSWORD_LENGTH: int = 8
ADMIN_USERNAME: str = _required_env("ADMIN_USERNAME")
ADMIN_EMAIL: str = _required_env("ADMIN_EMAIL")
ADMIN_PASSWORD: str = _required_env("ADMIN_PASSWORD")
if len(ADMIN_PASSWORD) < MIN_PASSWORD_LENGTH:
    raise RuntimeError("ADMIN_PASSWORD must satisfy the minimum password length.")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
CORS_ORIGINS: list[str] = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

                                                                               
                                     
HF_TOKEN: str = os.getenv("HF_TOKEN") or os.getenv("hf_token") or ""
                                                                        
HF_MODEL: str = os.getenv("HF_MODEL", "Qwen/Qwen3-32B")
                                         
HF_RAG_MODEL: str = os.getenv("HF_RAG_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
