"""
Utility helpers for data parsing and cleaning.
"""
import re
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace('\n', ' ').replace('\r', ' ')
    return text.strip()


def parse_salary(salary_text: str) -> dict:
    """Parse salary string into structured data."""
    if not salary_text:
        return {'raw': '', 'min': None, 'max': None, 'currency': 'USD', 'period': 'year'}

    salary_text = salary_text.replace(',', '')
    numbers = re.findall(r'\$?(\d+(?:\.\d+)?)[kK]?', salary_text)
    values = []
    for n in numbers:
        val = float(n)
        if 'k' in salary_text.lower() and val < 1000:
            val *= 1000
        if val > 10:  # Filter noise
            values.append(val)

    period = 'year'
    if any(w in salary_text.lower() for w in ['hour', 'hr', '/h']):
        period = 'hour'
    elif any(w in salary_text.lower() for w in ['month', 'mo']):
        period = 'month'

    return {
        'raw': salary_text,
        'min': min(values) if values else None,
        'max': max(values) if values else None,
        'currency': 'USD',
        'period': period
    }


def parse_relative_date(date_str: str) -> Optional[datetime]:
    """Convert relative date strings to datetime objects."""
    if not date_str:
        return None
    date_str = date_str.lower().strip()

    try:
        # ISO format
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return datetime.fromisoformat(date_str[:10])

        now = datetime.utcnow()

        if 'just posted' in date_str or 'today' in date_str or 'just now' in date_str:
            return now

        match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)', date_str)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            deltas = {
                'second': timedelta(seconds=num),
                'minute': timedelta(minutes=num),
                'hour': timedelta(hours=num),
                'day': timedelta(days=num),
                'week': timedelta(weeks=num),
                'month': timedelta(days=num * 30),
                'year': timedelta(days=num * 365)
            }
            return now - deltas.get(unit, timedelta(0))
    except Exception as e:
        logger.debug(f"Date parse error for '{date_str}': {e}")

    return None


def paginate(data: list, page: int, per_page: int) -> dict:
    """Paginate a list."""
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': data[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page)
    }