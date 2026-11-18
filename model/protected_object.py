from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProtectedObject:
    id: str
    name: str
    object_type: str
    sla_id: str | None = None
    sla_name: str | None = None
    search_term: str | None = None
    location: str | None = None

    def __str__(self):
        return f"Object(id={self.id}, name={self.name}, type={self.object_type})"


@dataclass
class MSSQLRecoveryPoint:
    hostname: str
    database_name: str
    lastest_log_recovery_point: datetime
    last_full_backup: datetime | None = None
    object_id: str | None = None
    object_name: str | None = None
    object_type: str | None = None
