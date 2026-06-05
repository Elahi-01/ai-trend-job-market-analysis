"""
Application configuration for AI Trend Job Market Analysis.

The project supports both the original environment names and the common
MongoDB Atlas names used during deployment.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # Product metadata
    PROJECT_NAME = os.environ.get("PROJECT_NAME", "AI Trend Job Market Analysis")
    PROJECT_TAGLINE = os.environ.get("PROJECT_TAGLINE", "Real-time AI-powered hiring trend intelligence")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.2")
    DEVELOPED_BY = os.environ.get("DEVELOPED_BY", "MD FAZLEY ELAHI")

    # Admin access. Change ADMIN_PASSWORD in production.
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Backwards compatible MongoDB environment variables
    MONGODB_URI = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGODB_DB = os.environ.get("MONGODB_DB") or os.environ.get("DATABASE_NAME", "job_market_analyzer")

    DEBUG = False
    TESTING = False

    SCRAPING_DELAY = float(os.environ.get("SCRAPING_DELAY", 2.0))
    MAX_JOBS_PER_SCRAPE = int(os.environ.get("MAX_JOBS_PER_SCRAPE", 50))
    DEFAULT_SCRAPE_KEYWORD = os.environ.get("DEFAULT_SCRAPE_KEYWORD", "software engineer")
    DEFAULT_SCRAPE_LOCATION = os.environ.get("DEFAULT_SCRAPE_LOCATION", "United States")

    # Scheduler controls. Disable in CI/test if needed with SCHEDULER_ENABLED=false.
    SCHEDULER_ENABLED = _bool_env("SCHEDULER_ENABLED", "true")
    DAILY_SCRAPE_HOUR = int(os.environ.get("DAILY_SCRAPE_HOUR", 8))
    WEEKLY_ANALYTICS_DAY = os.environ.get("WEEKLY_ANALYTICS_DAY", "mon")
    MONTHLY_ANALYTICS_DAY = int(os.environ.get("MONTHLY_ANALYTICS_DAY", 1))

    # Playwright fallback behaviour
    ENABLE_LIVE_SCRAPING = _bool_env("ENABLE_LIVE_SCRAPING", "true")

    # Public suggestion/message system. Uses SMTP, so no extra package is required.
    MAIL_ENABLED = _bool_env("MAIL_ENABLED", "false")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool_env("MAIL_USE_TLS", "true")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_RECEIVER = os.environ.get("MAIL_RECEIVER", "")


class DevelopmentConfig(Config):
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SCHEDULER_ENABLED = False
    MONGODB_DB = os.environ.get("MONGODB_TEST_DB", "job_market_analyzer_test")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
