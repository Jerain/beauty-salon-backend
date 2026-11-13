"""Custom types for Pydantic schemas to handle browser date formats."""
from datetime import datetime
from typing import Annotated
from pydantic import BeforeValidator


def _parse_datetime(v):
    """Parse datetime, handling browser ISO format with Z suffix.
    Converts to naive datetime (strips timezone) for DB compatibility.
    """
    if isinstance(v, str):
        # Replace Z suffix with +00:00 for Python 3.10 fromisoformat compatibility
        v = v.replace('Z', '+00:00')
        dt = datetime.fromisoformat(v)
    elif isinstance(v, datetime):
        dt = v
    else:
        return v
    # Strip timezone info to match database TIMESTAMP WITHOUT TIME ZONE
    return dt.replace(tzinfo=None)


BrowserDatetime = Annotated[datetime, BeforeValidator(_parse_datetime)]
