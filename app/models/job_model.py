"""
Job document model with validation and metadata helpers.
"""
from datetime import datetime
import hashlib
from typing import Optional, List


class JobModel:
    """Represents a job posting document."""

    REQUIRED_FIELDS = ["title", "company", "source"]

    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def generate_job_id(title: str, company: str, source: str, job_url: str = "") -> str:
        """Generate stable unique job ID from URL when available, otherwise key fields."""
        raw = job_url.strip() or f"{title.lower().strip()}|{company.lower().strip()}|{source.lower().strip()}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def date_parts(dt: Optional[datetime] = None) -> dict:
        """Return normalized daily/weekly/monthly fields for analytics."""
        dt = dt or datetime.utcnow()
        iso = dt.isocalendar()
        return {
            "date_scraped": dt.date().isoformat(),
            "day": dt.day,
            "week_number": iso.week,
            "month": dt.month,
            "year": dt.year,
        }

    @staticmethod
    def create(
        title: str,
        company: str,
        location: str,
        source: str,
        job_url: str = "",
        salary: str = "",
        description: str = "",
        skills: Optional[List[str]] = None,
        is_remote: bool = False,
        posted_date: Optional[datetime] = None,
        employment_type: str = "Full-time",
        search_mode: str = "keyword_location",
    ) -> dict:
        """Create a validated job document."""
        now = datetime.utcnow()
        job_id = JobModel.generate_job_id(title, company, source, job_url)
        doc = {
            "job_id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip() if location else "Not specified",
            "source": source,
            "job_url": job_url.strip() if job_url else "",
            "salary": salary.strip() if salary else "Not specified",
            "description": description[:3000] if description else "",
            "skills": skills or [],
            "is_remote": bool(is_remote),
            "posted_date": posted_date or now,
            "employment_type": employment_type or "Not specified",
            "search_mode": search_mode,
            "is_demo": search_mode == "demo",
            "data_scope": "demo" if search_mode == "demo" else "real",
            "scraped_at": now,
            "updated_at": now,
        }
        doc.update(JobModel.date_parts(now))
        return doc

    @staticmethod
    def ensure_metadata(job: dict, search_mode: str = "keyword_location") -> dict:
        """Add missing analytics metadata to a scraped job without mutating caller data."""
        now = datetime.utcnow()
        clean_job = dict(job or {})
        clean_job.setdefault("scraped_at", now)
        clean_job.setdefault("updated_at", now)
        clean_job.setdefault("search_mode", search_mode)
        clean_job.setdefault("is_demo", clean_job.get("search_mode") == "demo")
        clean_job.setdefault("data_scope", "demo" if clean_job.get("search_mode") == "demo" or clean_job.get("is_demo") is True else "real")
        clean_job.setdefault("is_remote", False)
        clean_job.setdefault("skills", [])
        clean_job.setdefault("salary", "Not specified")
        clean_job.setdefault("location", "Not specified")
        clean_job.update(JobModel.date_parts(clean_job.get("scraped_at") if hasattr(clean_job.get("scraped_at"), "date") else now))
        if not clean_job.get("job_id"):
            clean_job["job_id"] = JobModel.generate_job_id(
                clean_job.get("title", ""), clean_job.get("company", ""), clean_job.get("source", ""), clean_job.get("job_url", "")
            )
        return clean_job

    @staticmethod
    def validate(job: dict) -> bool:
        """Validate job document has required fields."""
        return all(job.get(field) and str(job.get(field)).strip() for field in JobModel.REQUIRED_FIELDS)
