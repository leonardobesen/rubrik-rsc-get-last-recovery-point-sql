import logging
from datetime import datetime, timezone
from typing import Any

from model.protected_object import ProtectedObject

logger = logging.getLogger(__name__)


def create_object_from_data(data: dict) -> ProtectedObject | None:
    """Create a protected-object model from GraphQL search results."""
    try:
        protect_obj = ProtectedObject(
            id=data["id"],
            name=data["name"],
            object_type=data["objectType"],
            sla_id=data.get("effectiveSlaDomain", {}).get("id", ""),
            sla_name=data.get("effectiveSlaDomain", {}).get("name", ""),
            is_relic=bool(data.get("isRelic", False)),
        )
        protect_obj.location = data.get("hostAddress", "")
        return protect_obj
    except KeyError as e:
        logger.error("Missing expected object data field: %s", e, exc_info=True)
    except Exception:
        logger.exception("Unexpected error while creating ProtectedObject")
    return None


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            logger.warning("Unable to parse datetime value: %s", value)
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def extract_latest_mssql_recovery_points(workload: ProtectedObject, recoverable_ranges: list[dict]) -> list[dict]:
    """Return the newest recoverable end time for an MSSQL workload."""
    lastest_log_recovery_point: datetime | None = None

    for recoverable_range in recoverable_ranges or []:
        end_time = _parse_iso_datetime(recoverable_range.get("endTime"))
        if end_time is None:
            continue
        if lastest_log_recovery_point is None or end_time > lastest_log_recovery_point:
            lastest_log_recovery_point = end_time

    if lastest_log_recovery_point is None:
        return []

    hostname = workload.location or workload.search_term or ""
    return [{
        "hostname": hostname,
        "databaseName": workload.name,
        "lastest_log_recovery_point": lastest_log_recovery_point,
        "last_full_backup": None,
    }]
