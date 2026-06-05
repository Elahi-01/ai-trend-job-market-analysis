"""
Indeed job scraper using Playwright and BeautifulSoup.
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.models.job_model import JobModel
from app.utils.skill_extractor import SkillExtractor
from app.utils.helpers import parse_salary, parse_relative_date, clean_text

logger = logging.getLogger(__name__)


class IndeedScraper:
    BASE_URL = "https://www.indeed.com/jobs"
    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    def __init__(self, delay: float = 2.5, max_jobs: int = 50):
        self.delay = delay
        self.max_jobs = max_jobs
        self.skill_extractor = SkillExtractor()

    async def scrape(self, keyword: str, location: str) -> List[Dict]:
        jobs = []
        url = self._build_url(keyword, location)
        logger.info(f"Indeed scraping: {keyword} in {location}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox',
                          '--disable-dev-shm-usage', '--disable-gpu']
                )
                context = await browser.new_context(
                    user_agent=self.HEADERS['User-Agent'],
                    viewport={'width': 1280, 'height': 900},
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    }
                )
                page = await context.new_page()

                try:
                    await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                    await asyncio.sleep(3)

                    # Handle potential popups
                    try:
                        close_btn = await page.query_selector('[aria-label="close"]')
                        if close_btn:
                            await close_btn.click()
                    except Exception:
                        pass

                    for _ in range(4):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)

                    html = await page.content()
                    jobs = self._parse_jobs(html)
                    logger.info(f"Indeed: found {len(jobs)} jobs")

                except PlaywrightTimeout:
                    logger.warning("Indeed page load timeout")
                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Indeed scraping error: {e}")

        return jobs[:self.max_jobs]

    def _build_url(self, keyword: str, location: str) -> str:
        from urllib.parse import urlencode
        params = {
            'q': keyword,
            'fromage': '1',  # Last 1 day
            'sort': 'date'
        }
        if location and location.strip():
            params['l'] = location.strip()
        return f"{self.BASE_URL}?{urlencode(params)}"

    def _parse_jobs(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # Indeed job cards
        job_cards = soup.find_all('div', class_=re.compile(r'job_seen_beacon|resultContent|jobsearch-SerpJobCard'))
        if not job_cards:
            job_cards = soup.find_all('td', class_=re.compile(r'resultContent'))

        for card in job_cards:
            try:
                job = self._extract_job_from_card(card)
                if job and JobModel.validate(job):
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Error parsing Indeed card: {e}")
                continue

        return jobs

    def _extract_job_from_card(self, card) -> Optional[Dict]:
        # Title
        title_el = (
            card.find('h2', class_=re.compile(r'jobTitle')) or
            card.find('a', class_=re.compile(r'jobtitle'))
        )
        if not title_el:
            return None
        title = clean_text(title_el.get_text())

        # Company
        company_el = (
            card.find('span', class_=re.compile(r'companyName|company')) or
            card.find('a', class_=re.compile(r'companyName'))
        )
        company = clean_text(company_el.get_text()) if company_el else 'Unknown'

        # Location
        location_el = card.find('div', class_=re.compile(r'companyLocation|location'))
        location = clean_text(location_el.get_text()) if location_el else 'Unknown'

        # Salary
        salary_el = card.find('div', class_=re.compile(r'salary-snippet|estimated-salary'))
        salary = clean_text(salary_el.get_text()) if salary_el else ''

        # Job URL
        link_el = card.find('a', href=re.compile(r'/rc/clk|/pagead/clk'))
        job_url = ''
        if link_el:
            href = link_el.get('href', '')
            job_url = f"https://www.indeed.com{href}" if href.startswith('/') else href

        # Remote
        is_remote = any(
            word in (title + location).lower()
            for word in ['remote', 'work from home', 'wfh', 'hybrid']
        )

        # Date
        date_el = card.find('span', class_=re.compile(r'date|posted'))
        posted_date = datetime.utcnow()
        if date_el:
            date_text = date_el.get_text().lower()
            posted_date = parse_relative_date(date_text) or datetime.utcnow()

        # Description snippet
        desc_el = card.find('div', class_=re.compile(r'job-snippet|summary'))
        description = clean_text(desc_el.get_text()) if desc_el else ''

        # Skills from title + description
        skills = self.skill_extractor.extract_from_text(f"{title} {description}")

        return JobModel.create(
            title=title,
            company=company,
            location=location,
            source='indeed',
            job_url=job_url,
            salary=salary,
            description=description,
            skills=skills,
            is_remote=is_remote,
            posted_date=posted_date
        )

    def scrape_sync(self, keyword: str, location: str) -> List[Dict]:
        return asyncio.run(self.scrape(keyword, location))