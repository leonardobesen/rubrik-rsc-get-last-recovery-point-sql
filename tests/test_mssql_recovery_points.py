import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from controller import controller
from data import data_parser
from data.data_operation import extract_latest_mssql_recovery_points
from file_manager.write_to_file import _normalize_output_datetime
from model.protected_object import ProtectedObject


class MSSQLRecoveryPointsTest(unittest.TestCase):
    def test_extract_latest_mssql_recovery_point_uses_max_end_time(self):
        workload = ProtectedObject(
            id="workload-1",
            name="CustomerOrders",
            object_type="Mssql",
            search_term="sql-host-01",
            location="sql-host-01",
        )
        ranges = [
            {"beginTime": "2024-01-01T00:00:00Z", "endTime": "2024-01-02T00:00:00Z"},
            {"beginTime": "2024-01-05T00:00:00Z", "endTime": "2024-01-06T00:00:00Z"},
            {"beginTime": "2024-01-03T00:00:00Z", "endTime": "2024-01-04T00:00:00Z"},
        ]

        actual = extract_latest_mssql_recovery_points(workload, ranges)

        self.assertEqual(
            actual,
            [{
                "hostname": "sql-host-01",
                "databaseName": "CustomerOrders",
                "lastest_log_recovery_point": datetime.fromisoformat("2024-01-06T00:00:00+00:00"),
                "last_full_backup": None,
            }],
        )

    def test_extract_latest_mssql_recovery_point_falls_back_to_search_term(self):
        workload = ProtectedObject(
            id="workload-2",
            name="Accounting",
            object_type="MssqlAvailabilityGroup",
            search_term="sql-ag-01",
        )

        actual = extract_latest_mssql_recovery_points(
            workload,
            [{"endTime": "2026-01-15T12:30:00Z"}],
        )

        self.assertEqual(actual[0]["hostname"], "sql-ag-01")
        self.assertEqual(actual[0]["databaseName"], "Accounting")

    def test_extract_latest_mssql_recovery_point_handles_empty_or_invalid_ranges(self):
        workload = ProtectedObject(id="workload-3", name="Sales", object_type="Mssql")

        self.assertEqual(extract_latest_mssql_recovery_points(workload, []), [])
        self.assertEqual(
            extract_latest_mssql_recovery_points(workload, [{"endTime": "not-a-date"}]),
            [],
        )

    def test_parse_hostnames_from_rubrik_report_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "rubrik_export.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Cluster", "LOCATION", "Object", "Object State", "Last Successful Backup"])
                writer.writerow(["bkp-pd-0001", "sql-host-01", "CustomerOrders", "Active", "11/16/2026 12:23:09 PM"])
                writer.writerow(["bkp-pd-0001", "sql-host-02, sql-ag-01", "Accounting", "Active", "11/16/2026 11:41:23 AM"])

            parsed = controller._read_hostnames_from_file(csv_path)

        self.assertEqual(parsed, ["sql-host-01", "sql-host-02", "sql-ag-01"])

    def test_parse_hostnames_deduplicates_instance_fqdn_and_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "rubrik_export.csv"
            csv_path.write_text(
                "Cluster,Location,Object,Object State,Last Successful Backup\n"
                "bkp-pd-0012,CHFRXZ203692A.bkp.tesp7.local\\PROTHEUS,msdb,Active,11/18/2026 04:08:11 AM\n"
                "bkp-pd-0012,CHFRXZ203692A.bkp.tesp7.local,master,Active,11/18/2026 04:08:11 AM\n"
                "bkp-pd-0012,CHFRXZ203692A,C0KXAQ_217932_TS_DV,Active,11/18/2026 04:08:11 AM\n",
                encoding="utf-8",
            )

            parsed = controller._read_hostnames_from_file(csv_path)

        self.assertEqual(parsed, ["CHFRXZ203692A"])

    def test_canonical_hostname_is_case_insensitive_for_deduplication(self):
        raw_value = "CHFRXZ203692A.bkp.tesp7.local\\PROTHEUS, chfrxz203692a"

        self.assertEqual(
            controller._normalize_hostname_values(raw_value),
            ["CHFRXZ203692A"],
        )

    def test_canonical_hostname_preserves_ip_address(self):
        self.assertEqual(
            controller._normalize_hostname_values("10.20.30.40"),
            ["10.20.30.40"],
        )

    def test_normalize_output_datetime_uses_brazil_timezone(self):
        self.assertEqual(
            _normalize_output_datetime("2024-01-08T00:00:00+00:00"),
            "2024-01-07T21:00:00-03:00",
        )

    @patch("data.data_parser.request")
    def test_workflow_attaches_latest_full_backup(self, mock_request):
        mock_request.side_effect = [
            {"data": {"mssqlRecoverableRanges": {"data": [{"endTime": "2026-01-10T10:00:00Z"}]}}},
            {"data": {"snappableConnection": {"nodes": [{"lastSnapshot": "2026-01-09T08:30:00Z"}]}}},
        ]
        workload = ProtectedObject(
            id="workload-4",
            name="Finance",
            object_type="Mssql",
            location="sql-host-04",
        )

        points = data_parser.get_latest_recovery_points_for_workload("token", workload)

        self.assertEqual(points[0]["lastest_log_recovery_point"].isoformat(), "2026-01-10T10:00:00+00:00")
        self.assertEqual(points[0]["last_full_backup"].isoformat(), "2026-01-09T08:30:00+00:00")


if __name__ == "__main__":
    unittest.main()
