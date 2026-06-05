"""APScheduler integration for automated scraping and analytics snapshots."""
import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.analysis.analytics_engine import AnalyticsEngine
from app.services.scraping_service import ScrapingService, SearchModes

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def daily_scrape_job(app):
    """Daily automation: scrape configured keyword/location and refresh analytics."""
    with app.app_context():
        keyword = app.config.get("DEFAULT_SCRAPE_KEYWORD", "software engineer")
        location = app.config.get("DEFAULT_SCRAPE_LOCATION", "United States")
        logger.info("Daily scheduled scrape started: %s / %s", keyword, location)
        service = ScrapingService(app.db_manager, app.config)
        result = service.run({
            "search_mode": SearchModes.KEYWORD_LOCATION,
            "keyword": keyword,
            "location": location,
            "sources": ["linkedin", "indeed"],
        })
        logger.info("Daily scheduled scrape finished: %s", result.get("results"))


def daily_analytics_job(app):
    """Generate daily snapshot."""
    with app.app_context():
        snapshot = AnalyticsEngine(app.db_manager).generate_daily_snapshot()
        logger.info("Daily analytics snapshot generated for %s", snapshot.get("date"))


def weekly_analytics_job(app):
    """Generate weekly snapshot."""
    with app.app_context():
        snapshot = AnalyticsEngine(app.db_manager).generate_weekly_snapshot()
        logger.info("Weekly analytics snapshot generated for %s", snapshot.get("period"))


def monthly_analytics_job(app):
    """Generate monthly snapshot."""
    with app.app_context():
        snapshot = AnalyticsEngine(app.db_manager).generate_monthly_snapshot()
        logger.info("Monthly analytics snapshot generated for %s", snapshot.get("period"))


def init_scheduler(app):
    """Attach scheduler to Flask app once per process."""
    if not app.config.get("SCHEDULER_ENABLED", True):
        logger.info("Scheduler disabled by configuration")
        return None

    # Avoid duplicate scheduler in Werkzeug reloader.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logger.info("Skipping scheduler in parent debug process")
        return None

    if scheduler.running:
        return scheduler

    daily_hour = int(app.config.get("DAILY_SCRAPE_HOUR", 8))
    weekly_day = app.config.get("WEEKLY_ANALYTICS_DAY", "mon")
    monthly_day = int(app.config.get("MONTHLY_ANALYTICS_DAY", 1))

    scheduler.add_job(
        daily_scrape_job,
        CronTrigger(hour=daily_hour, minute=0),
        args=[app],
        id="daily_scrape_job",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        daily_analytics_job,
        CronTrigger(hour=daily_hour, minute=30),
        args=[app],
        id="daily_analytics_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        weekly_analytics_job,
        CronTrigger(day_of_week=weekly_day, hour=daily_hour + 1, minute=0),
        args=[app],
        id="weekly_analytics_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        monthly_analytics_job,
        CronTrigger(day=monthly_day, hour=daily_hour + 2, minute=0),
        args=[app],
        id="monthly_analytics_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    app.scheduler = scheduler
    logger.info("Scheduler started at %s with daily hour=%s UTC", datetime.utcnow().isoformat(), daily_hour)
    return scheduler
