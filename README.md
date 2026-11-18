# MSSQL Recovery Point Reporter

This utility searches Rubrik RSC for Microsoft SQL Server database and Availability Group workloads by hostname, gets the latest recoverable range for each matching workload, and exports the newest recovery point to CSV.

## What it does

- Reads hostnames from a CSV file in the `reports/input` folder.
- Supports a simple one-host-per-row CSV or a Rubrik export CSV containing a `Location` column.
- Queries RSC for active MSSQL database and MSSQL Availability Group objects.
- Calls `mssqlRecoverableRanges` for each matching workload.
- Keeps the newest valid `endTime` returned for each database workload.
- Saves the result to the `reports` folder and logs skipped or failed records under `logs`.

## Requirements

- Python 3.10+
- Network access to the Rubrik RSC tenant
- A Rubrik RSC service account with access to the MSSQL workloads

## Installation

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Update `configuration/config.json` with the Rubrik RSC tenant values:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "name": "service_account_name",
  "access_token_uri": "https://yourdomain.my.rubrik.com/api/client_token",
  "graphql_url": "https://yourdomain.my.rubrik.com/api/graphql",
  "tz_info": "America/Sao_Paulo"
}
```

`tz_info` must be a valid IANA timezone name. It defaults to `UTC` if omitted or empty.

## Input file

Place one CSV file in `reports/input`.

Simple hostname list:

```csv
sql-host-01
sql-host-02
sql-ag-01
```

Rubrik export format:

```csv
Cluster,Location,Object,Object State
cluster-01,sql-host-01,CustomerOrders,Active
cluster-01,"sql-host-02, sql-ag-01",Accounting,Active
```

The parser accepts a `Location` header regardless of letter case. Comma-separated Location values are split into individual hostnames.

Before querying RSC, locations are canonicalized to the base hostname: SQL Server instances after `\` and DNS suffixes after `.` are removed. Repeated variants such as `HOST.bkp.example.local\INSTANCE`, `HOST.bkp.example.local`, and `HOST` are treated as one case-insensitive hostname and searched once.

## Run

```bash
python main.py --input hostname_list.csv
```

If `--input` is omitted, the script lists the available CSV files and prompts for a selection.

## Output

The script writes a CSV with a name such as:

```text
reports/MSSQL_Recovery_Points_18-11-2026_14_30_00.csv
```

Columns:

- `hostname`: the hostname or Availability Group search term associated with the workload
- `databaseName`: the MSSQL database or workload name
- `lastest_log_recovery_point`: newest log recovery end time converted to the configured timezone
- `last_full_backup`: latest MSSQL snapshot/full-backup date converted to the configured timezone

## Logging

Runtime information and warnings are written to `logs/mssql_lookup_errors.log`.

The run continues when a hostname is not found or a workload has no recoverable range. Review the log for skipped records and query failures.

## Troubleshooting

- Verify the service account can access the MSSQL workloads in RSC.
- Confirm hostnames exactly match the names used by Rubrik.
- Confirm `mssqlRecoverableRanges` is available for the MSSQL workload type in the tenant GraphQL schema.
- Verify `tz_info` is a valid IANA timezone.
- Review `logs/mssql_lookup_errors.log` for skipped records and query failures.
