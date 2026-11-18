import logging
from pathlib import Path

import connection.connect as connect
import file_manager.write_to_file as write_to_file
from configuration.configuration import get_root_dir
from controller import controller


def configure_logging() -> None:
    log_dir = Path(get_root_dir()) / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "mssql_lookup_errors.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


if __name__ == '__main__':
    configure_logging()
    logger = logging.getLogger(__name__)
    args = controller.parse_command_line_args()

    rsc_access_token = connect.open_session()
    try:
        hostnames = controller.parse_csv_files(csv_filename=args.input)

        print("Collecting MSSQL recovery points...")
        logger.info("Starting MSSQL recovery-point lookup for %s hostnames", len(hostnames))
        recovery_points = controller.get_mssql_recovery_points(
            access_token=rsc_access_token,
            hostnames=hostnames,
        )

        if not recovery_points:
            logger.warning("No MSSQL recovery points were found for the provided hostnames.")

        print("Writing to file...")
        file_path = write_to_file.generate_mssql_recovery_report(
            report_name="MSSQL_Recovery_Points",
            rows=recovery_points,
        )

        print(f"Saved to file {file_path}")
    finally:
        connect.close_session(rsc_access_token)
