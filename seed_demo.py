"""Seed MongoDB with realistic demo-only jobs.

Demo seed data is isolated for Static Demo Mode. It does not update real
analytics snapshots and it never appears in public Jobs/CSV export.
"""
from app import create_app
from app.analysis.analytics_engine import AnalyticsEngine
from app.services.demo_data import seed_demo_data

app = create_app()

with app.app_context():
    result = seed_demo_data(app.db_manager, count=100)
    analytics = AnalyticsEngine(app.db_manager, demo_only=True).get_all_analytics()
    print("Demo-only data seeded:", result)
    print("Demo dashboard URL: http://127.0.0.1:5000/dashboard/demo")
    print("Demo analytics total jobs:", analytics.get("overview", {}).get("total_jobs", 0))
