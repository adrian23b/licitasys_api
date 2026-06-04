from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.logging import get_logger


PERU_TZ = ZoneInfo("America/Lima")
logger = get_logger(__name__)


def parse_seace_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=PERU_TZ)
    if not isinstance(value, str) or not value.strip():
        return None

    value = value.strip()
    for date_format in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.replace(tzinfo=PERU_TZ)
        except ValueError:
            continue

    logger.warning("malformed_seace_datetime", value=value)
    return None


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    return " ".join(text.split()) if text else None
