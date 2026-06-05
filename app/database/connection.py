"""
MongoDB connection manager with collection setup, indexes, and optimized accessors.
"""
import logging
import os
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton MongoDB manager used by Flask routes and background jobs."""

    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize MongoDB connection and setup collections/indexes."""
        uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.environ.get("MONGODB_DB") or os.environ.get("DATABASE_NAME", "job_market_analyzer")
        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=7000, retryWrites=True)
            self._client.admin.command("ping")
            self._db = self._client[db_name]
            self._setup_collections()
            logger.info("Connected to MongoDB database=%s", db_name)
        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as exc:
            logger.error("MongoDB connection failed: %s", exc)
            raise

    def _safe_create_index(self, collection, keys, **kwargs):
        try:
            collection.create_index(keys, **kwargs)
        except OperationFailure as exc:
            logger.warning("Index creation skipped for %s: %s", collection.name, exc)

    def _setup_collections(self):
        """Create collections and indexes safely without removing existing data."""
        db = self._db

        # Jobs: duplicate prevention + fast search/filtering.
        self._safe_create_index(db.jobs, [("job_id", ASCENDING)], unique=True, name="uniq_job_id")
        self._safe_create_index(db.jobs, [("job_url", ASCENDING)], sparse=True, name="idx_job_url")
        self._safe_create_index(db.jobs, [("title", TEXT), ("company", TEXT), ("skills", TEXT), ("description", TEXT)], name="txt_job_search")
        self._safe_create_index(db.jobs, [("scraped_at", DESCENDING)], name="idx_scraped_at")
        self._safe_create_index(db.jobs, [("date_scraped", DESCENDING)], name="idx_date_scraped")
        self._safe_create_index(db.jobs, [("posted_date", DESCENDING)], name="idx_posted_date")
        self._safe_create_index(db.jobs, [("location", ASCENDING)], name="idx_location")
        self._safe_create_index(db.jobs, [("source", ASCENDING)], name="idx_source")
        self._safe_create_index(db.jobs, [("search_mode", ASCENDING)], name="idx_search_mode")
        self._safe_create_index(db.jobs, [("data_scope", ASCENDING)], name="idx_data_scope")
        self._safe_create_index(db.jobs, [("is_demo", ASCENDING)], name="idx_is_demo")
        self._safe_create_index(db.jobs, [("is_remote", ASCENDING)], name="idx_is_remote")
        self._safe_create_index(db.jobs, [("week_number", ASCENDING), ("year", ASCENDING)], name="idx_week_year")
        self._safe_create_index(db.jobs, [("month", ASCENDING), ("year", ASCENDING)], name="idx_month_year")

        # Operational logs.
        self._safe_create_index(db.scraping_logs, [("timestamp", DESCENDING)], name="idx_log_timestamp")
        self._safe_create_index(db.scraping_logs, [("source", ASCENDING)], name="idx_log_source")
        self._safe_create_index(db.scraping_logs, [("status", ASCENDING)], name="idx_log_status")
        self._safe_create_index(db.scraping_logs, [("search_mode", ASCENDING)], name="idx_log_search_mode")

        # Historical analytics collections.
        self._safe_create_index(db.daily_analytics, [("date", DESCENDING)], unique=True, name="uniq_daily_date")
        self._safe_create_index(db.daily_analytics, [("data_scope", ASCENDING), ("date", DESCENDING)], name="idx_daily_scope_date")
        self._safe_create_index(db.daily_analytics, [("year", ASCENDING), ("month", ASCENDING), ("day", ASCENDING)], name="idx_daily_parts")
        self._safe_create_index(db.weekly_analytics, [("year", ASCENDING), ("week_number", ASCENDING)], unique=True, name="uniq_week")
        self._safe_create_index(db.weekly_analytics, [("data_scope", ASCENDING), ("year", ASCENDING), ("week_number", ASCENDING)], name="idx_week_scope")
        self._safe_create_index(db.monthly_analytics, [("year", ASCENDING), ("month", ASCENDING)], unique=True, name="uniq_month")
        self._safe_create_index(db.monthly_analytics, [("data_scope", ASCENDING), ("year", ASCENDING), ("month", ASCENDING)], name="idx_month_scope")

        # Suggestions/messages from public feedback form.
        self._safe_create_index(db.messages, [("created_at", DESCENDING)], name="idx_message_created_at")
        self._safe_create_index(db.messages, [("status", ASCENDING)], name="idx_message_status")
        self._safe_create_index(db.messages, [("category", ASCENDING)], name="idx_message_category")

        # Keep legacy analytics collection for backwards compatibility.
        self._safe_create_index(db.analytics, [("date", DESCENDING)], name="idx_legacy_date")
        self._safe_create_index(db.analytics, [("metric_type", ASCENDING)], name="idx_legacy_metric")

        logger.info("MongoDB collections and indexes configured")

    @property
    def db(self):
        if self._db is None:
            self.initialize()
        return self._db

    @property
    def jobs(self):
        return self.db.jobs

    @property
    def analytics(self):
        return self.db.analytics

    @property
    def scraping_logs(self):
        return self.db.scraping_logs

    @property
    def daily_analytics(self):
        return self.db.daily_analytics

    @property
    def weekly_analytics(self):
        return self.db.weekly_analytics

    @property
    def monthly_analytics(self):
        return self.db.monthly_analytics

    @property
    def messages(self):
        return self.db.messages

    def close(self):
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Global instance
_db_manager = DatabaseManager()
db_manager = _db_manager
