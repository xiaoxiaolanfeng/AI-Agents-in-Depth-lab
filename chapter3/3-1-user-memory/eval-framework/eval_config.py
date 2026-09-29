"""Configuration module for User Memory Evaluation Framework."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _openrouter_model_id(model) -> str:
    """Map a provider-native model name to an OpenRouter model id, used by the
    universal OpenRouter fallback. An explicit OPENROUTER_MODEL env var wins."""
    override = os.getenv("OPENROUTER_MODEL")
    if override:
        return override
    m = (model or "").strip()
    if not m:
        return "openai/gpt-5.6-luna"
    if "/" in m:
        return m
    ml = m.lower()
    if ml.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
        return "openai/" + m
    if ml.startswith("claude-"):
        return "anthropic/claude-opus-4.8"
    if ml.startswith("kimi"):
        # kimi-k3 is not on OpenRouter; moonshotai/kimi-k2.6 is the closest hosted id.
        return "moonshotai/kimi-k2.6"
    return "openai/gpt-5.6-luna"


class Config:
    """Configuration settings for the evaluation framework."""

    # Kimi API Settings (also accept MOONSHOT_API_KEY for compatibility)
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY", "")
    KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    KIMI_MODEL: str = os.getenv("KIMI_MODEL", "kimi-k3")

    # OpenAI API Settings (alternative)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    # OpenRouter fallback settings (used when the primary judge key is missing)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Evaluation Settings
    DEFAULT_EVALUATOR: str = os.getenv("DEFAULT_EVALUATOR", "kimi")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
    
    # Test Case Settings
    TEST_CASES_DIR: str = os.path.join(os.path.dirname(__file__), "test_cases")
    
    @classmethod
    def get_evaluator_config(cls, evaluator: Optional[str] = None) -> dict:
        """Get configuration for the specified evaluator."""
        evaluator = evaluator or cls.DEFAULT_EVALUATOR
        
        if evaluator == "kimi":
            if cls.KIMI_API_KEY:
                return {
                    "api_key": cls.KIMI_API_KEY,
                    "base_url": cls.KIMI_BASE_URL,
                    "model": cls.KIMI_MODEL,
                    "type": "kimi"
                }
            if cls.OPENROUTER_API_KEY:
                return {
                    "api_key": cls.OPENROUTER_API_KEY,
                    "base_url": cls.OPENROUTER_BASE_URL,
                    "model": _openrouter_model_id(cls.KIMI_MODEL),
                    "type": "openrouter"
                }
            raise ValueError(
                "KIMI_API_KEY not configured. Set KIMI_API_KEY/MOONSHOT_API_KEY "
                "or OPENROUTER_API_KEY (fallback) in .env file."
            )
        elif evaluator == "openai":
            # gpt-5.x (incl. gpt-5.6*) needs OpenAI org-verification on the direct
            # API; when an OpenRouter key is present, prefer routing it through OR.
            prefer_openrouter = (bool(cls.OPENROUTER_API_KEY)
                                 and cls.OPENAI_MODEL.lower().startswith("gpt-5"))
            if cls.OPENAI_API_KEY and not prefer_openrouter:
                return {
                    "api_key": cls.OPENAI_API_KEY,
                    "base_url": cls.OPENAI_BASE_URL,
                    "model": cls.OPENAI_MODEL,
                    "type": "openai"
                }
            if cls.OPENROUTER_API_KEY:
                return {
                    "api_key": cls.OPENROUTER_API_KEY,
                    "base_url": cls.OPENROUTER_BASE_URL,
                    "model": _openrouter_model_id(cls.OPENAI_MODEL),
                    "type": "openrouter"
                }
            raise ValueError(
                "OPENAI_API_KEY not configured. Set OPENAI_API_KEY or "
                "OPENROUTER_API_KEY (fallback) in .env file."
            )
        else:
            raise ValueError(f"Unknown evaluator: {evaluator}. Supported: kimi, openai")
