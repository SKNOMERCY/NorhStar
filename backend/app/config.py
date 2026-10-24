import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BASE_DIR.parent
DB_PATH = os.path.join(BASE_DIR, "northstar.db")

class Settings(BaseModel):
    APP_NAME: str = "Northstar - AI Agent Long-Horizon Goal Tracking System"
    VERSION: str = "2.0.0"
    DB_PATH: str = DB_PATH
    WORKSPACE_ROOT: str = str(WORKSPACE_ROOT)
    
    # AI Provider configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    
    # Drift thresholds
    DRIFT_NORMAL_MAX: float = 0.25      # < 0.25: Aligned (True Bearing)
    DRIFT_WARNING_MAX: float = 0.50     # 0.25 - 0.50: Warning (Grounding Reminder)
    DRIFT_INTERVENE_MAX: float = 0.75   # 0.50 - 0.75: Intervene (Circuit Breaker)
    # > 0.75: Critical (Hazard divergence / Abort)
    
    # Weight factors for composite drift calculation
    WEIGHT_SEMANTIC: float = 0.45
    WEIGHT_CONSTRAINT: float = 0.40
    WEIGHT_HORIZON_DECAY: float = 0.15

settings = Settings()
