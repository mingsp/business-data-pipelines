from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class DimensionConfig:
    name: str
    data_source_name: str
    view_code: str
    target_table: str
    expected_task_prefix: str
    selected_data_codes: list[str]
    has_store_column: bool
    has_active_store_count: bool


@dataclass(frozen=True)
class Store:
    store_id: str
    store_name: str


@dataclass(frozen=True)
class ExportStatus:
    data_source_name: str
    store_id: str
    store_name: str
    start_date: date
    end_date: date
    create_time: datetime
    export_before_time: datetime
    export_after_time: datetime
    status: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True)
class ExportTask:
    task_name: str
    executing_state: Optional[str]
    op_time: Optional[datetime]
    download_url: Optional[str]
