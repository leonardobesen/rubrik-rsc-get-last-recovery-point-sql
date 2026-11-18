import os
from datetime import datetime, timezone

import pandas as pd
from zoneinfo import ZoneInfo

from configuration.configuration import get_root_dir, get_timezone_info


def _normalize_output_datetime(value):
    if value is None:
        return ""

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    else:
        dt = value

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(ZoneInfo(get_timezone_info())).isoformat(timespec="seconds")


def _create_empty_file(report_name: str) -> str:
    now = datetime.now().strftime("%d-%m-%Y_%H_%M_%S")
    file_name = f'{report_name}_{now}.csv'
    report_path = os.path.join(get_root_dir(), 'reports', file_name)
    return report_path


def generate_mssql_recovery_report(report_name: str, rows: list[dict]) -> str:
    report_file = _create_empty_file(report_name)

    processed_rows = []
    for row in rows:
        processed_row = dict(row)
        processed_row["lastest_log_recovery_point"] = _normalize_output_datetime(
            processed_row.get("lastest_log_recovery_point")
        )
        processed_row["last_full_backup"] = _normalize_output_datetime(
            processed_row.get("last_full_backup")
        )
        processed_rows.append(processed_row)

    columns = [
        "hostname",
        "databaseName",
        "objectStatus",
        "lastest_log_recovery_point",
        "last_full_backup",
    ]
    df = pd.DataFrame(processed_rows, columns=columns)
    df.to_csv(report_file, index=False)

    return report_file
