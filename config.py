import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "database" / "portal.db"


def _database_uri() -> str:
    # Railway / hosted deployment: set DATABASE_URL to a sqlite:// URL pointing
    # at a path on a persistent volume, e.g. sqlite:////data/portal.db
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"


class BaseConfig:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "phase1-insecure-dev-key")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # PORT is honored by gunicorn (via Procfile $PORT) on Railway; the Flask
    # dev server uses its own --port flag. Surfaced here for any code that
    # needs to read it.
    PORT = int(os.getenv("PORT", "5000"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
