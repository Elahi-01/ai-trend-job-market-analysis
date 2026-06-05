"""Service layer for search modes, scraping orchestration, job persistence, and readable logs."""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.analysis.analytics_engine import AnalyticsEngine
from app.models.job_model import JobModel
from app.scrapers.indeed_scraper import IndeedScraper
from app.scrapers.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)


class SearchModes:
    KEYWORD_ONLY = "keyword_only"
    KEYWORD_LOCATION = "keyword_location"
    DEMO = "demo"

    ALL = {KEYWORD_ONLY, KEYWORD_LOCATION, DEMO}


class ScrapingService:
    """Coordinates all scraping flows while preserving existing scraper classes."""

    def __init__(self, db_manager, config: Optional[dict] = None):
        self.db = db_manager
        self.config = config or {}

    def normalize_payload(self, data: dict) -> dict:
        """Validate and normalize search-mode input from the UI/API."""
        search_mode = (data.get("search_mode") or data.get("mode") or SearchModes.KEYWORD_LOCATION).strip()
        if search_mode not in SearchModes.ALL:
            raise ValueError("Invalid search mode")

        keyword = (data.get("keyword") or self.config.get("DEFAULT_SCRAPE_KEYWORD") or "software engineer").strip()
        location = (data.get("location") or self.config.get("DEFAULT_SCRAPE_LOCATION") or "").strip()
        sources = data.get("sources") or ["linkedin", "indeed"]
        sources = [source for source in sources if source in {"linkedin", "indeed"}]

        if search_mode == SearchModes.DEMO:
            return {"search_mode": search_mode, "keyword": "", "location": "", "sources": []}

        if not keyword or len(keyword) > 100:
            raise ValueError("Invalid keyword. Please enter 1 to 100 characters.")

        if search_mode == SearchModes.KEYWORD_ONLY:
            location = ""
        elif not location or len(location) > 100:
            raise ValueError("Invalid location. Please enter 1 to 100 characters.")

        if not sources:
            raise ValueError("Select at least one scraping source")

        return {"search_mode": search_mode, "keyword": keyword, "location": location, "sources": sources}

    def run(self, payload: dict) -> Dict:
        """Execute a search mode. Demo mode never launches Playwright."""
        request_data = self.normalize_payload(payload)
        if request_data["search_mode"] == SearchModes.DEMO:
            return self.load_demo_dashboard()

        if not self.config.get("ENABLE_LIVE_SCRAPING", True):
            raise RuntimeError("Live scraping is disabled by ENABLE_LIVE_SCRAPING=false")

        start = time.time()
        results = {
            "linkedin": self.empty_source_stats(),
            "indeed": self.empty_source_stats(),
            "total_fetched": 0,
            "total_new": 0,
            "total_duplicates": 0,
            "total_failed": 0,
        }
        status = "success"

        for source in request_data["sources"]:
            try:
                jobs = self._run_source(source, request_data["keyword"], request_data["location"])
                save_result = self.save_jobs(jobs, source=source, search_mode=request_data["search_mode"])
                source_stats = self.build_source_stats(fetched=len(jobs), **save_result)
                results[source] = source_stats
                results["total_fetched"] += source_stats["fetched"]
                results["total_new"] += source_stats["inserted"]
                results["total_duplicates"] += source_stats["duplicates"]
                results["total_failed"] += source_stats["failed"]
                if source_stats["failed"] > 0 and status == "success":
                    status = "success_with_warnings"
            except Exception as exc:
                logger.exception("%s scraping failed", source)
                status = "partial_error"
                results[source] = self.build_source_stats(fetched=0, inserted=0, duplicates=0, failed=1, error=str(exc))
                results["total_failed"] += 1

        duration = round(time.time() - start, 2)
        self.log_run(request_data, results, duration, status)

        snapshots = {}
        try:
            snapshots = AnalyticsEngine(self.db).refresh_all_snapshots()
        except Exception as exc:
            logger.warning("Analytics refresh failed after scraping: %s", exc)

        return {
            "success": True,
            "mode": request_data["search_mode"],
            "keyword": request_data["keyword"],
            "location": request_data["location"],
            "results": results,
            "duration": duration,
            "snapshots_updated": bool(snapshots),
        }

    @staticmethod
    def empty_source_stats() -> Dict[str, int]:
        """Default stats shape used by API, logs, and UI."""
        return {
            "fetched": 0,
            "scraped": 0,  # backward-compatible alias for old frontend/log entries
            "inserted": 0,
            "duplicates": 0,
            "failed": 0,
        }

    @staticmethod
    def build_source_stats(fetched: int, inserted: int, duplicates: int, failed: int, error: Optional[str] = None) -> Dict:
        """Build readable source-level stats: Fetched / Inserted / Duplicate / Failed."""
        stats = {
            "fetched": int(fetched or 0),
            "scraped": int(fetched or 0),  # legacy alias
            "inserted": int(inserted or 0),
            "duplicates": int(duplicates or 0),
            "failed": int(failed or 0),
        }
        if error:
            stats["error"] = error
        return stats

    def _run_source(self, source: str, keyword: str, location: str) -> List[dict]:
        max_jobs = int(self.config.get("MAX_JOBS_PER_SCRAPE", 50))
        if source == "linkedin":
            scraper = LinkedInScraper(delay=float(self.config.get("SCRAPING_DELAY", 2.0)), max_jobs=max_jobs)
            return scraper.scrape_sync(keyword, location)
        if source == "indeed":
            scraper = IndeedScraper(delay=float(self.config.get("SCRAPING_DELAY", 2.5)), max_jobs=max_jobs)
            return scraper.scrape_sync(keyword, location)
        raise ValueError(f"Unknown source: {source}")

    def save_jobs(self, jobs: List[dict], source: str, search_mode: str) -> Dict[str, int]:
        """Save jobs using upsert result counts and duplicate-safe persistence."""
        inserted = 0
        duplicates = 0
        failed = 0

        for raw_job in jobs:
            try:
                job = JobModel.ensure_metadata(raw_job, search_mode=search_mode)
                job["source"] = job.get("source") or source

                if not JobModel.validate(job):
                    failed += 1
                    continue

                # MongoDB does not allow the same field in $setOnInsert and $set.
                # The scraped job already contains updated_at, so keep it out of
                # $setOnInsert and let $set handle last_seen/updated timestamps.
                now = datetime.utcnow()
                insert_doc = {
                    key: value
                    for key, value in job.items()
                    if key not in {"updated_at", "last_seen_at"}
                }

                result = self.db.jobs.update_one(
                    {"job_id": job["job_id"]},
                    {
                        "$setOnInsert": insert_doc,
                        "$set": {
                            "updated_at": now,
                            "last_seen_at": now,
                        },
                    },
                    upsert=True,
                )

                if result.upserted_id:
                    inserted += 1
                else:
                    duplicates += 1
            except Exception as exc:
                logger.debug("Save job error: %s", exc)
                failed += 1

        return {"inserted": inserted, "duplicates": duplicates, "failed": failed}

    def log_run(self, request_data: dict, results: dict, duration: float, status: str) -> None:
        """Persist scraping log in a clear, audit-friendly shape."""
        self.db.scraping_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "keyword": request_data.get("keyword", ""),
            "location": request_data.get("location", ""),
            "search_mode": request_data.get("search_mode", SearchModes.KEYWORD_LOCATION),
            "sources": request_data.get("sources", []),
            "results": results,
            "summary": {
                "total_fetched": results.get("total_fetched", 0),
                "total_inserted": results.get("total_new", 0),
                "total_duplicates": results.get("total_duplicates", 0),
                "total_failed": results.get("total_failed", 0),
            },
            "duration_seconds": duration,
            "status": status,
        })

    def load_demo_dashboard(self) -> Dict:
        """Return demo-only analytics instantly without launching Playwright."""
        analytics = AnalyticsEngine(self.db, demo_only=True).get_all_analytics()
        self.db.scraping_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "keyword": "",
            "location": "",
            "search_mode": SearchModes.DEMO,
            "sources": [],
            "results": {
                "demo": True,
                "linkedin": self.empty_source_stats(),
                "indeed": self.empty_source_stats(),
                "total_fetched": 0,
                "total_new": 0,
                "total_duplicates": 0,
                "total_failed": 0,
            },
            "summary": {
                "total_fetched": 0,
                "total_inserted": 0,
                "total_duplicates": 0,
                "total_failed": 0,
            },
            "duration_seconds": 0,
            "status": "demo_loaded",
        })
        return {"success": True, "mode": SearchModes.DEMO, "demo": True, "analytics": analytics, "dashboard_url": "/dashboard/demo"}
