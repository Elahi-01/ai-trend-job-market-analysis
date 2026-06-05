"""Demo data loader used by recruiter showcase/static demo mode."""
from datetime import datetime, timedelta
import random

from app.models.job_model import JobModel

DEMO_COMPANIES = ["Pathao", "Brain Station 23", "TigerIT", "ShopUp", "bKash", "Optimizely", "DataSoft", "Samsung R&D"]
DEMO_TITLES = [
    "Python Developer", "Data Analyst", "Machine Learning Engineer", "Backend Engineer",
    "Frontend Developer", "DevOps Engineer", "Full Stack Engineer", "Business Intelligence Analyst",
]
DEMO_LOCATIONS = ["Dhaka", "Remote", "Chattogram", "Bangladesh", "Gulshan, Dhaka", "Banani, Dhaka"]
DEMO_SKILLS = ["Python", "Flask", "MongoDB", "Pandas", "React", "SQL", "AWS", "Docker", "Machine Learning", "JavaScript", "Power BI"]


def seed_demo_data(db_manager, count: int = 80) -> dict:
    """Seed demo-only records used exclusively by Static Demo Mode.

    Demo records are marked with search_mode=demo/is_demo=True/data_scope=demo
    and intentionally do not contain fake clickable job URLs. This keeps
    dashboard/jobs/export clean for real scraped jobs.
    """
    # Normalize older demo rows from previous versions so example.com links never leak into exports/UI.
    db_manager.jobs.update_many(
        {"$or": [{"search_mode": "demo"}, {"is_demo": True}, {"data_scope": "demo"}]},
        {"$set": {"search_mode": "demo", "is_demo": True, "data_scope": "demo"}, "$unset": {"job_url": ""}},
    )

    inserted = 0
    duplicates = 0
    now = datetime.utcnow()
    for i in range(count):
        title = random.choice(DEMO_TITLES)
        company = random.choice(DEMO_COMPANIES)
        location = random.choice(DEMO_LOCATIONS)
        source = random.choice(["linkedin", "indeed"])
        posted = now - timedelta(days=random.randint(0, 60))
        skills = random.sample(DEMO_SKILLS, k=random.randint(3, 6))
        job = JobModel.create(
            title=f"{title} {i+1}",
            company=company,
            location=location,
            source=source,
            job_url="",
            salary=random.choice(["$60k - $90k a year", "$90k - $130k a year", "Not specified", "৳80,000 - ৳150,000 monthly"]),
            description=f"Demo role requiring {', '.join(skills)}.",
            skills=skills,
            is_remote="remote" in location.lower() or random.random() > 0.65,
            posted_date=posted,
            employment_type=random.choice(["Full-time", "Contract", "Hybrid"]),
            search_mode="demo",
        )
        job["is_demo"] = True
        job["data_scope"] = "demo"
        job.pop("job_url", None)
        # Make historical charts meaningful by shifting scraped_at too.
        job["scraped_at"] = posted
        job["updated_at"] = now
        job.update(JobModel.date_parts(posted))
        result = db_manager.jobs.update_one({"job_id": job["job_id"]}, {"$setOnInsert": job}, upsert=True)
        if result.upserted_id:
            inserted += 1
        else:
            duplicates += 1
    return {"inserted": inserted, "duplicates": duplicates, "requested": count}
