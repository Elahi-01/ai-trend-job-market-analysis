"""
LinkedIn job scraper using Playwright and BeautifulSoup.
Handles dynamic content, pagination, and rate limiting.
"""
import asyncio
import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.models.job_model import JobModel
from app.utils.skill_extractor import SkillExtractor
from app.utils.helpers import parse_salary, parse_relative_date, clean_text

logger = logging.getLogger(__name__)


class LinkedInScraper:
    BASE_URL = "https://www.linkedin.com/jobs/search"
    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    def __init__(self, delay: float = 2.0, max_jobs: int = 50):
        self.delay = delay
        self.max_jobs = max_jobs
        self.skill_extractor = SkillExtractor()

    async def scrape(self, keyword: str, location: str) -> List[Dict]:
        """Main scraping method - returns list of job dicts."""
        jobs = []
        url = self._build_url(keyword, location)
        logger.info(f"LinkedIn scraping: {keyword} in {location}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox',
                          '--disable-dev-shm-usage', '--disable-gpu']
                )
                context = await browser.new_context(
                    user_agent=self.HEADERS['User-Agent'],
                    viewport={'width': 1280, 'height': 800}
                )
                page = await context.new_page()

                try:
                    await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                    await asyncio.sleep(2)

                    # Scroll to load more jobs
                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1.5)

                    html = await page.content()
                    jobs = self._parse_jobs(html, keyword)
                    logger.info(f"LinkedIn: found {len(jobs)} jobs")

                except PlaywrightTimeout:
                    logger.warning("LinkedIn page load timeout")
                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"LinkedIn scraping error: {e}")

        return jobs[:self.max_jobs]

    def _build_url(self, keyword: str, location: str) -> str:
        from urllib.parse import urlencode, quote_plus
        params = {
            'keywords': keyword,
            'f_TPR': 'r86400',  # Last 24 hours
            'sortBy': 'DD'
        }
        if location and location.strip():
            params['location'] = location.strip()
        return f"{self.BASE_URL}?{urlencode(params)}"

    def _parse_jobs(self, html: str, keyword: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # LinkedIn job cards
        job_cards = soup.find_all('div', class_=re.compile(r'job-search-card|base-card'))
        if not job_cards:
            job_cards = soup.find_all('li', class_=re.compile(r'jobs-search-results__list-item'))

        for card in job_cards:
            try:
                job = self._extract_job_from_card(card)
                if job and JobModel.validate(job):
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Error parsing LinkedIn card: {e}")
                continue

        return jobs

    def _extract_job_from_card(self, card) -> Optional[Dict]:
        # Title
        title_el = (
            card.find('h3', class_=re.compile(r'base-search-card__title|job-search-card__title')) or
            card.find('a', class_=re.compile(r'job-title'))
        )
        if not title_el:
            return None
        title = clean_text(title_el.get_text())

        # Company
        company_el = (
            card.find('h4', class_=re.compile(r'base-search-card__subtitle')) or
            card.find('a', class_=re.compile(r'hidden-nested-link'))
        )
        company = clean_text(company_el.get_text()) if company_el else 'Unknown'

        # Location
        location_el = card.find('span', class_=re.compile(r'job-search-card__location|base-search-card__metadata'))
        location = clean_text(location_el.get_text()) if location_el else 'Unknown'

        # Job URL
        link_el = card.find('a', href=True)
        job_url = link_el['href'] if link_el else ''
        if job_url and not job_url.startswith('http'):
            job_url = 'https://www.linkedin.com' + job_url

        # Remote detection
        is_remote = any(
            word in (title + location).lower()
            for word in ['remote', 'work from home', 'wfh', 'hybrid']
        )

        # Salary (rare on LinkedIn cards)
        salary_el = card.find('span', class_=re.compile(r'job-search-card__salary'))
        salary = clean_text(salary_el.get_text()) if salary_el else ''

        # Date
        date_el = card.find('time')
        if date_el:
            datetime_attr = date_el.get('datetime', '')
            posted_date = parse_relative_date(datetime_attr) or datetime.utcnow()
        else:
            posted_date = datetime.utcnow()

        # Skills from title
        skills = self.skill_extractor.extract_from_text(title)

        return JobModel.create(
            title=title,
            company=company,
            location=location,
            source='linkedin',
            job_url=job_url,
            salary=salary,
            skills=skills,
            is_remote=is_remote,
            posted_date=posted_date
        )

    def scrape_sync(self, keyword: str, location: str) -> List[Dict]:
        """Synchronous wrapper for Flask routes."""
        return asyncio.run(self.scrape(keyword, location))