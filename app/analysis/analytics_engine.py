"""
Analytics engine using MongoDB aggregation, Pandas, and NumPy.

Professional data-scope behavior:
- Default analytics are REAL data only.
- Demo analytics are available only when demo_only=True.
- Demo jobs never pollute Dashboard, Jobs list, CSV export, or scheduled snapshots.
"""
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Chart-ready and snapshot analytics for the Job Market Intelligence platform."""

    REAL_SCOPE_MATCH = {
        "$and": [
            {"search_mode": {"$ne": "demo"}},
            {"is_demo": {"$ne": True}},
            {"data_scope": {"$ne": "demo"}},
        ]
    }
    DEMO_SCOPE_MATCH = {
        "$or": [
            {"search_mode": "demo"},
            {"is_demo": True},
            {"data_scope": "demo"},
        ]
    }

    def __init__(self, db_manager, *, demo_only: bool = False, include_demo: bool = False):
        self.db = db_manager
        self.demo_only = demo_only
        self.include_demo = include_demo
        if demo_only:
            self.scope_name = "demo"
            self.scope_match = self.DEMO_SCOPE_MATCH
        elif include_demo:
            self.scope_name = "all"
            self.scope_match = {}
        else:
            self.scope_name = "real"
            self.scope_match = self.REAL_SCOPE_MATCH

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------
    def _merge_match(self, *parts: Optional[dict]) -> dict:
        """Safely combine MongoDB match dictionaries without key collisions."""
        active = [part for part in parts if part]
        if not active:
            return {}
        if len(active) == 1:
            return active[0]
        return {"$and": active}

    def _match(self, extra: Optional[dict] = None) -> dict:
        """Return query match for the current data scope."""
        return self._merge_match(self.scope_match, extra or {})

    def _date_range_match(self, start: datetime, end: datetime) -> dict:
        return {"scraped_at": {"$gte": start, "$lt": end}}

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------
    def _get_jobs_df(self, days: Optional[int] = 30) -> pd.DataFrame:
        """Load scoped jobs into a DataFrame for analytics."""
        query = {}
        if days:
            query["scraped_at"] = {"$gte": datetime.utcnow() - timedelta(days=days)}
        jobs = list(self.db.jobs.find(self._match(query), {"_id": 0}))
        if not jobs:
            return pd.DataFrame()
        df = pd.DataFrame(jobs)
        for field in ["posted_date", "scraped_at", "updated_at"]:
            if field in df.columns:
                df[field] = pd.to_datetime(df[field], errors="coerce")
        return df

    # ------------------------------------------------------------------
    # Real-time dashboard analytics
    # ------------------------------------------------------------------
    def get_overview_stats(self) -> Dict[str, Any]:
        """Get high-level summary statistics for the selected scope."""
        try:
            now = datetime.utcnow()
            current_week = {"scraped_at": {"$gte": now - timedelta(days=7)}}
            previous_week = {"scraped_at": {"$gte": now - timedelta(days=14), "$lt": now - timedelta(days=7)}}

            total_jobs = self.db.jobs.count_documents(self._match())
            recent_jobs = self.db.jobs.count_documents(self._match(current_week))
            last_week_jobs = self.db.jobs.count_documents(self._match(previous_week))
            remote_jobs = self.db.jobs.count_documents(self._match({"is_remote": True}))
            total_companies = len([c for c in self.db.jobs.distinct("company", self._match()) if c])
            linkedin_jobs = self.db.jobs.count_documents(self._match({"source": "linkedin"}))
            indeed_jobs = self.db.jobs.count_documents(self._match({"source": "indeed"}))

            remote_pct = round((remote_jobs / total_jobs * 100) if total_jobs else 0, 1)
            growth = 0
            if last_week_jobs:
                growth = round(((recent_jobs - last_week_jobs) / last_week_jobs) * 100, 1)
            elif recent_jobs:
                growth = 100

            return {
                "total_jobs": int(total_jobs),
                "recent_jobs": int(recent_jobs),
                "remote_jobs": int(remote_jobs),
                "remote_percentage": remote_pct,
                "total_companies": int(total_companies),
                "linkedin_jobs": int(linkedin_jobs),
                "indeed_jobs": int(indeed_jobs),
                "weekly_growth": growth,
                "data_scope": self.scope_name,
                "last_updated": now.isoformat(),
            }
        except Exception as exc:
            logger.error("Overview stats error: %s", exc)
            return {"data_scope": self.scope_name}

    def get_top_companies(self, limit: int = 10, match: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Get companies with most job postings for selected scope."""
        try:
            pipeline = [
                {"$match": self._match(match)},
                {"$match": {"company": {"$nin": [None, "", "Unknown"]}}},
                {"$group": {"_id": "$company", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": int(limit)},
            ]
            return [{"company": r["_id"], "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]
        except Exception as exc:
            logger.error("Top companies error: %s", exc)
            return []

    def get_top_skills(self, limit: int = 15, days: Optional[int] = 30, match: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Get most in-demand skills for selected scope."""
        try:
            time_match = {}
            if days:
                time_match["scraped_at"] = {"$gte": datetime.utcnow() - timedelta(days=days)}
            pipeline = [
                {"$match": self._match(self._merge_match(time_match, match or {}))},
                {"$unwind": "$skills"},
                {"$match": {"skills": {"$nin": [None, ""]}}},
                {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": int(limit)},
            ]
            return [{"skill": r["_id"], "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]
        except Exception as exc:
            logger.error("Top skills error: %s", exc)
            return []

    def get_remote_vs_onsite(self, match: Optional[dict] = None) -> Dict[str, int]:
        """Get remote vs onsite job counts for selected scope."""
        try:
            remote_query = self._match(self._merge_match(match or {}, {"is_remote": True}))
            onsite_query = self._match(self._merge_match(match or {}, {"is_remote": {"$ne": True}}))
            return {
                "remote": int(self.db.jobs.count_documents(remote_query)),
                "onsite": int(self.db.jobs.count_documents(onsite_query)),
            }
        except Exception as exc:
            logger.error("Remote vs onsite error: %s", exc)
            return {"remote": 0, "onsite": 0}

    def get_daily_trends(self, days: int = 14) -> List[Dict[str, Any]]:
        """Get daily scraped job trend for selected scope."""
        try:
            start = datetime.utcnow() - timedelta(days=days - 1)
            pipeline = [
                {"$match": self._match({"scraped_at": {"$gte": start}})},
                {"$group": {"_id": "$date_scraped", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]
            rows = list(self.db.jobs.aggregate(pipeline, allowDiskUse=True))
            existing = {r["_id"]: int(r["count"]) for r in rows if r.get("_id")}
            output = []
            for i in range(days):
                d = (datetime.utcnow() - timedelta(days=days - 1 - i)).date().isoformat()
                output.append({"date": d, "count": existing.get(d, 0)})
            return output
        except Exception as exc:
            logger.error("Daily trends error: %s", exc)
            return []

    def get_location_analytics(self, limit: int = 10, match: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Get city-wise job distribution for selected scope."""
        try:
            pipeline = [
                {"$match": self._match(match)},
                {"$match": {"location": {"$nin": [None, "", "Unknown", "Not specified"]}}},
                {"$group": {"_id": "$location", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": int(limit)},
            ]
            return [{"location": r["_id"], "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]
        except Exception as exc:
            logger.error("Location analytics error: %s", exc)
            return []

    def get_salary_distribution(self, match: Optional[dict] = None) -> Dict[str, Any]:
        """Analyze salary data for selected scope."""
        try:
            salary_filter = {"salary": {"$nin": ["Not specified", "", None]}}
            cursor = self.db.jobs.find(self._match(self._merge_match(match or {}, salary_filter)), {"salary": 1, "_id": 0})
            salaries = [doc.get("salary", "") for doc in cursor]
            from app.utils.helpers import parse_salary

            parsed = [parse_salary(salary) for salary in salaries]
            values = [
                item["min"] for item in parsed
                if item.get("min") and item.get("period") == "year" and 20000 < item["min"] < 500000
            ]
            if not values:
                return {"ranges": [], "average": 0, "median": 0}
            arr = np.array(values)
            ranges = [
                {"range": "<$50k", "count": int(np.sum(arr < 50000))},
                {"range": "$50k-$80k", "count": int(np.sum((arr >= 50000) & (arr < 80000)))},
                {"range": "$80k-$120k", "count": int(np.sum((arr >= 80000) & (arr < 120000)))},
                {"range": "$120k-$160k", "count": int(np.sum((arr >= 120000) & (arr < 160000)))},
                {"range": "$160k+", "count": int(np.sum(arr >= 160000))},
            ]
            return {
                "ranges": [r for r in ranges if r["count"] > 0],
                "average": int(np.mean(arr)),
                "median": int(np.median(arr)),
            }
        except Exception as exc:
            logger.error("Salary distribution error: %s", exc)
            return {"ranges": [], "average": 0, "median": 0}

    def get_source_breakdown(self, match: Optional[dict] = None) -> List[Dict[str, Any]]:
        """Jobs breakdown by scraping source for selected scope."""
        try:
            pipeline = [
                {"$match": self._match(match)},
                {"$group": {"_id": "$source", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            return [{"source": r.get("_id") or "unknown", "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]
        except Exception as exc:
            logger.error("Source breakdown error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Historical analytics for daily/weekly/monthly systems
    # ------------------------------------------------------------------
    def get_weekly_skill_growth(self, weeks: int = 6, limit: int = 5) -> Dict[str, Any]:
        """Return chart-ready multi-line weekly skill growth data for selected scope."""
        try:
            now = datetime.utcnow()
            min_date = now - timedelta(weeks=weeks)
            top_skills = [item["skill"] for item in self.get_top_skills(limit=limit, days=weeks * 7)]
            if not top_skills:
                return {"labels": [], "datasets": []}

            pipeline = [
                {"$match": self._match({"scraped_at": {"$gte": min_date}, "skills": {"$in": top_skills}})},
                {"$unwind": "$skills"},
                {"$match": {"skills": {"$in": top_skills}}},
                {"$group": {"_id": {"year": "$year", "week": "$week_number", "skill": "$skills"}, "count": {"$sum": 1}}},
                {"$sort": {"_id.year": 1, "_id.week": 1}},
            ]
            rows = list(self.db.jobs.aggregate(pipeline, allowDiskUse=True))
            labels = []
            current = date.today()
            for i in range(weeks - 1, -1, -1):
                d = current - timedelta(weeks=i)
                iso = d.isocalendar()
                labels.append(f"{iso.year}-W{iso.week:02d}")
            counts = {skill: {label: 0 for label in labels} for skill in top_skills}
            for row in rows:
                key = row["_id"]
                label = f"{key.get('year')}-W{int(key.get('week', 0)):02d}"
                skill = key.get("skill")
                if skill in counts and label in counts[skill]:
                    counts[skill][label] = int(row["count"])
            return {
                "labels": labels,
                "datasets": [{"skill": skill, "data": [counts[skill][label] for label in labels]} for skill in top_skills],
            }
        except Exception as exc:
            logger.error("Weekly skill growth error: %s", exc)
            return {"labels": [], "datasets": []}

    def get_monthly_heatmap(self, months: int = 6) -> List[Dict[str, Any]]:
        """Return month x source heatmap values for selected scope."""
        try:
            start = datetime.utcnow() - timedelta(days=months * 31)
            pipeline = [
                {"$match": self._match({"scraped_at": {"$gte": start}})},
                {"$group": {"_id": {"year": "$year", "month": "$month", "source": "$source"}, "count": {"$sum": 1}}},
                {"$sort": {"_id.year": 1, "_id.month": 1}},
            ]
            output = []
            for row in self.db.jobs.aggregate(pipeline, allowDiskUse=True):
                key = row["_id"]
                output.append({
                    "period": f"{key.get('year')}-{int(key.get('month', 1)):02d}",
                    "source": key.get("source") or "unknown",
                    "count": int(row["count"]),
                })
            return output
        except Exception as exc:
            logger.error("Monthly heatmap error: %s", exc)
            return []

    def get_historical_summary(self) -> Dict[str, Any]:
        """Return saved scoped daily/weekly/monthly snapshots for dashboards."""
        try:
            scope_filter = {"data_scope": self.scope_name}
            daily = list(self.db.daily_analytics.find(scope_filter, {"_id": 0}).sort("date", -1).limit(30))
            weekly = list(self.db.weekly_analytics.find(scope_filter, {"_id": 0}).sort([("year", -1), ("week_number", -1)]).limit(12))
            monthly = list(self.db.monthly_analytics.find(scope_filter, {"_id": 0}).sort([("year", -1), ("month", -1)]).limit(12))
            return {"daily": list(reversed(daily)), "weekly": list(reversed(weekly)), "monthly": list(reversed(monthly))}
        except Exception as exc:
            logger.error("Historical summary error: %s", exc)
            return {"daily": [], "weekly": [], "monthly": []}

    def generate_daily_snapshot(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate and persist one daily analytics snapshot for selected scope."""
        target_date = target_date or datetime.utcnow().date()
        start = datetime.combine(target_date, datetime.min.time())
        end = start + timedelta(days=1)
        date_match = self._date_range_match(start, end)
        total = self.db.jobs.count_documents(self._match(date_match))
        remote = self.db.jobs.count_documents(self._match(self._merge_match(date_match, {"is_remote": True})))
        snapshot = {
            "data_scope": self.scope_name,
            "date": target_date.isoformat(),
            "day": target_date.day,
            "week_number": target_date.isocalendar().week,
            "month": target_date.month,
            "year": target_date.year,
            "job_count": int(total),
            "remote_count": int(remote),
            "remote_ratio": round((remote / total * 100) if total else 0, 1),
            "top_companies": self.get_top_companies(limit=10, match=date_match),
            "top_skills": self._top_skills_for_match(date_match, limit=15),
            "generated_at": datetime.utcnow(),
        }
        self.db.daily_analytics.update_one({"date": snapshot["date"], "data_scope": self.scope_name}, {"$set": snapshot}, upsert=True)
        return snapshot

    def _top_skills_for_match(self, match: dict, limit: int = 10) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": self._match(match)},
            {"$unwind": "$skills"},
            {"$match": {"skills": {"$nin": [None, ""]}}},
            {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": int(limit)},
        ]
        return [{"skill": r["_id"], "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]

    def generate_weekly_snapshot(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate and persist one weekly analytics snapshot for selected scope."""
        target_date = target_date or datetime.utcnow().date()
        iso = target_date.isocalendar()
        start = datetime.fromisocalendar(iso.year, iso.week, 1)
        end = start + timedelta(days=7)
        prev_start = start - timedelta(days=7)
        prev_end = start
        match = self._date_range_match(start, end)
        prev_match = self._date_range_match(prev_start, prev_end)
        total = self.db.jobs.count_documents(self._match(match))
        previous_total = self.db.jobs.count_documents(self._match(prev_match))
        growth = round(((total - previous_total) / previous_total * 100), 1) if previous_total else (100 if total else 0)
        snapshot = {
            "data_scope": self.scope_name,
            "year": iso.year,
            "week_number": iso.week,
            "period": f"{iso.year}-W{iso.week:02d}",
            "start_date": start.date().isoformat(),
            "end_date": (end - timedelta(days=1)).date().isoformat(),
            "job_count": int(total),
            "growth_percentage": growth,
            "top_companies": self.get_top_companies(limit=10, match=match),
            "top_skills": self._top_skills_for_match(match, limit=15),
            "remote_vs_onsite": self.get_remote_vs_onsite(match),
            "skill_growth": self.get_weekly_skill_growth(weeks=6, limit=5),
            "generated_at": datetime.utcnow(),
        }
        self.db.weekly_analytics.update_one(
            {"year": iso.year, "week_number": iso.week, "data_scope": self.scope_name}, {"$set": snapshot}, upsert=True
        )
        return snapshot

    def generate_monthly_snapshot(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Generate and persist one monthly analytics snapshot for selected scope."""
        target_date = target_date or datetime.utcnow().date()
        start = datetime(target_date.year, target_date.month, 1)
        end = datetime(target_date.year + (1 if target_date.month == 12 else 0), 1 if target_date.month == 12 else target_date.month + 1, 1)
        match = self._date_range_match(start, end)
        snapshot = {
            "data_scope": self.scope_name,
            "year": target_date.year,
            "month": target_date.month,
            "period": f"{target_date.year}-{target_date.month:02d}",
            "job_count": int(self.db.jobs.count_documents(self._match(match))),
            "top_technologies": self._top_skills_for_match(match, limit=20),
            "top_locations": self._locations_for_match(match, limit=12),
            "salary_trends": self.get_salary_distribution(match=match),
            "heatmap": self.get_monthly_heatmap(months=6),
            "generated_at": datetime.utcnow(),
        }
        self.db.monthly_analytics.update_one(
            {"year": target_date.year, "month": target_date.month, "data_scope": self.scope_name}, {"$set": snapshot}, upsert=True
        )
        return snapshot

    def _locations_for_match(self, match: dict, limit: int = 10) -> List[Dict[str, Any]]:
        pipeline = [
            {"$match": self._match(match)},
            {"$match": {"location": {"$nin": [None, "", "Unknown", "Not specified"]}}},
            {"$group": {"_id": "$location", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": int(limit)},
        ]
        return [{"location": r["_id"], "count": int(r["count"])} for r in self.db.jobs.aggregate(pipeline, allowDiskUse=True)]

    def refresh_all_snapshots(self) -> Dict[str, Any]:
        """Generate daily, weekly, and monthly snapshots for selected scope."""
        return {
            "daily": self.generate_daily_snapshot(),
            "weekly": self.generate_weekly_snapshot(),
            "monthly": self.generate_monthly_snapshot(),
        }

    def get_all_analytics(self) -> Dict[str, Any]:
        """Return all analytics in one call for selected scope."""
        return {
            "scope": self.scope_name,
            "overview": self.get_overview_stats(),
            "top_companies": self.get_top_companies(),
            "top_skills": self.get_top_skills(),
            "remote_vs_onsite": self.get_remote_vs_onsite(),
            "daily_trends": self.get_daily_trends(days=14),
            "weekly_skill_growth": self.get_weekly_skill_growth(weeks=6, limit=5),
            "monthly_heatmap": self.get_monthly_heatmap(months=6),
            "location_analytics": self.get_location_analytics(),
            "salary_distribution": self.get_salary_distribution(),
            "source_breakdown": self.get_source_breakdown(),
            "historical": self.get_historical_summary(),
        }
