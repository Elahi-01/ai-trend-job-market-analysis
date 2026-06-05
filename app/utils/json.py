"""JSON serialization helpers for MongoDB documents."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from bson import ObjectId


def json_safe(value: Any) -> Any:
    """Recursively convert MongoDB/Python values into JSON-safe values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value
