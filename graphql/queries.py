def search_mssql_object_by_hostname(hostname: str, cluster_ids: list[str] | None = None) -> tuple[str, dict]:
    """Search Rubrik RSC for MSSQL database and AG objects related to a hostname."""
    variables = {
        "filter": [
            {"field": "LOCATION", "texts": [hostname]},
            {"field": "IS_GHOST", "texts": ["false"]},
            {"field": "IS_ACTIVE", "texts": ["true"]},
        ],
        "sortBy": "NAME",
        "sortOrder": "ASC",
        "first": 300,
    }

    if cluster_ids:
        variables["filter"].append(
            {"field": "CLUSTER_ID", "texts": cluster_ids})

    query = """query MSSQLHostObjectSearch(
      $first: Int!,
      $filter: [Filter!]!,
      $sortBy: HierarchySortByField,
      $sortOrder: SortOrder
    ) {
      globalSearchResults(
        first: $first
        filter: $filter
        sortBy: $sortBy
        sortOrder: $sortOrder
      ) {
        nodes {
          id
          name
          objectType
          effectiveSlaDomain {
            id
            name
          }
        }
      }
    }"""

    return query, variables


def get_latest_recoverable_date(workload_id: str) -> tuple[str, dict]:
    """GraphQL query to get the latest recoverable date for an MSSQL workload."""
    variables = {
        "input": {
            "id": workload_id
        }
    }

    query = """query MSSQLRecoverableRanges($input: GetMssqlDbRecoverableRangesInput!) {
      mssqlRecoverableRanges(input: $input) {
        data {
          beginTime
          endTime
          status
          isMountAllowed
        }
      }
    }"""

    return query, variables


def get_mssql_full_backup_info(workload_id: str) -> tuple[str, dict]:
    """GraphQL query to get the latest snapshot for an MSSQL workload."""
    variables = {
        "filter": {
            "objectFid": workload_id
        }
    }

    query = """query SnapshotsListMssql($filter: SnappableFilterInput) {
      snappableConnection(filter: $filter) {
        nodes {
          fid
          lastSnapshot
        }
      }
    }"""

    return query, variables