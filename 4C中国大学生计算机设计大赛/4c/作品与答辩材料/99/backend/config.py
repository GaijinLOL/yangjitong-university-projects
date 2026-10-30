import os

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return v


class Config:
    # ====== LLM (DashScope / 通义千问) ======
    DASHSCOPE_API_KEY = _env("DASHSCOPE_API_KEY")
    LLM_MODEL = _env("LLM_MODEL", "qwen3.6-flash")

    # ====== Tushare ======
    TUSHARE_TOKEN = _env("TUSHARE_TOKEN")

    # ====== MySQL (local) ======
    MYSQL_HOST = _env("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(_env("MYSQL_PORT", "3306") or 3306)
    MYSQL_USER = _env("MYSQL_USER", "root")
    MYSQL_PASSWORD = _env("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE = _env("MYSQL_DATABASE", "enterprise_analysis")

    # ====== Flask ======
    FLASK_HOST = _env("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(_env("FLASK_PORT", "5000") or 5000)
    FLASK_DEBUG = (_env("FLASK_DEBUG", "1") == "1")


def validate_required_config() -> list[str]:
    missing: list[str] = []
    if not Config.TUSHARE_TOKEN:
        missing.append("TUSHARE_TOKEN")
    if not Config.DASHSCOPE_API_KEY:
        missing.append("DASHSCOPE_API_KEY")
    return missing


