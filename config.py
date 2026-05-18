import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "portal.db"


class BaseConfig:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "phase1-insecure-dev-key")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


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
