import logging

from tqdm import tqdm

import graphql.queries
from connection.wrapper import request
from data import data_operation
from model.protected_object import ProtectedObject

logger = logging.getLogger(__name__)


def get_mssql_protected_objects(
    access_token: str,
    hostnames: list[str],
    selected_clusters: list[str] | None = None,
) -> list[ProtectedObject]:
    """Query Rubrik RSC for MSSQL database and AG workloads that match the provided hostnames."""
    protected_objects: list[ProtectedObject] = []
    selected_clusters = selected_clusters or []

    for hostname in tqdm(hostnames, desc="Searching MSSQL hosts"):
        try:
            query, variables = graphql.queries.search_mssql_object_by_hostname(
                hostname=hostname,
                cluster_ids=selected_clusters,
            )
            response = request(access_token, query, variables)
            nodes = response.get("data", {}).get("globalSearchResults", {}).get("nodes", [])
        except Exception:
            logger.warning("Failed to fetch MSSQL object data for host %s", hostname)
            continue

        if not nodes:
            logger.warning("No MSSQL DB or AG objects found for hostname: %s", hostname)
            continue

        matched = 0
        for item in nodes:
            object_type = item.get("objectType")
            if object_type not in {"Mssql", "MssqlAvailabilityGroup"}:
                continue

            protected_object = data_operation.create_object_from_data(item)
            if protected_object is None:
                continue

            protected_object.search_term = hostname
            protected_object.location = protected_object.location or hostname
            protected_objects.append(protected_object)
            matched += 1

        if matched == 0:
            logger.warning(
                "No MSSQL Database or MSSQL AG workloads found for hostname %s in current search results.",
                hostname,
            )

    return protected_objects


def get_latest_recovery_points_for_workload(
    access_token: str,
    workload: ProtectedObject,
) -> list[dict]:
    """Fetch the latest recoverable range for an MSSQL workload."""
    try:
        query, variables = graphql.queries.get_latest_recoverable_date(workload.id)
        response = request(access_token, query, variables)
        ranges = response.get("data", {}).get("mssqlRecoverableRanges", {}).get("data", [])
    except Exception:
        logger.error("Failed to fetch recoverable range data for workload %s (%s)", workload.name, workload.id)
        return []

    if not ranges:
        logger.warning(
            "No recoverable ranges returned for workload %s (%s). This workload will be skipped.",
            workload.name,
            workload.id,
        )
        return []

    latest_points = data_operation.extract_latest_mssql_recovery_points(workload, ranges)
    if not latest_points:
        logger.warning(
            "No recoverable points were extracted for workload %s (%s).",
            workload.name,
            workload.id,
        )
        return []

    last_full_backup = None
    try:
        full_backup_query, full_backup_variables = graphql.queries.get_mssql_full_backup_info(workload.id)
        full_backup_response = request(access_token, full_backup_query, full_backup_variables)
        snappable_nodes = (
            full_backup_response.get("data", {})
            .get("snappableConnection", {})
            .get("nodes", [])
        )

        for node in snappable_nodes:
            snapshot = node.get("lastSnapshot")
            if isinstance(snapshot, dict):
                snapshot = snapshot.get("date") or snapshot.get("time") or snapshot.get("timestamp")
            snapshot_date = data_operation._parse_iso_datetime(snapshot)
            if snapshot_date is not None:
                if last_full_backup is None or snapshot_date > last_full_backup:
                    last_full_backup = snapshot_date
    except Exception:
        logger.exception("Failed to fetch full backup snapshot data for workload %s (%s)", workload.name, workload.id)

    for point in latest_points:
        point["last_full_backup"] = last_full_backup
        point["objectId"] = workload.id
        point["objectName"] = workload.name
        point["objectType"] = workload.object_type

    return latest_points
