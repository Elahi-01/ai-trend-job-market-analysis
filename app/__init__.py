"""Flask application factory."""
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, session

from config.settings import Config
from app.database.connection import DatabaseManager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    _configure_logging()
    logger = logging.getLogger(__name__)

    try:
        db_manager = DatabaseManager()
        db_manager.initialize()
        app.db_manager = db_manager
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        raise

    from app.routes.dashboard import dashboard_bp
    from app.routes.jobs import jobs_bp
    from app.routes.analytics import analytics_bp
    from app.routes.scraper import scraper_bp
    from app.routes.messages import messages_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(scraper_bp, url_prefix="/scraper")
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_project_meta():
        return {
            "project_name": app.config.get("PROJECT_NAME", "AI Trend Job Market Analysis"),
            "project_tagline": app.config.get("PROJECT_TAGLINE", "Real-time AI-powered hiring trend intelligence"),
            "app_version": app.config.get("APP_VERSION", "1.0.2"),
            "developed_by": app.config.get("DEVELOPED_BY", "MD FAZLEY ELAHI"),
            "admin_authenticated": bool(session.get("admin_authenticated")),
        }

    try:
        from app.scheduler.tasks import init_scheduler
        init_scheduler(app)
    except Exception as exc:
        # The web app should still boot even if scheduler cannot start.
        logger.warning("Scheduler initialization skipped/failed: %s", exc)

    @app.teardown_appcontext
    def _teardown(_exception=None):
        # Keep the shared MongoClient alive; closing per request hurts performance.
        return None

    return app


def _configure_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if root.handlers:
        return
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
