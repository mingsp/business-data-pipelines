from __future__ import annotations

import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from business_data_pipelines.core.config import RuntimeSettings
from business_data_pipelines.core.db import mysql_connection
from business_data_pipelines.pipelines.qnh.activity_detail.client import QnhClient
from business_data_pipelines.pipelines.qnh.activity_detail.config import DIMENSIONS
from business_data_pipelines.pipelines.qnh.activity_detail.importer import ActivityDetailImporter
from business_data_pipelines.pipelines.qnh.activity_detail.models import (
    DimensionConfig,
    ExportStatus,
    ExportTask,
    Store,
)
from business_data_pipelines.pipelines.qnh.activity_detail.repository import StatusRepository


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def safe_filename(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", value).strip()


class ActivityDetailPipeline:
    def __init__(
        self,
        *,
        settings: RuntimeSettings,
        dimension_name: str,
        start: date,
        end: date,
    ):
        if dimension_name not in DIMENSIONS:
            raise ValueError(f"Unknown dimension: {dimension_name}")
        self.settings = settings
        self.dimension = DIMENSIONS[dimension_name]
        self.start = start
        self.end = end
        self.pipeline_config = settings.config.get("qnh_activity_detail", {})
        self.download_dir = Path(self.pipeline_config.get("download_dir", "downloads/qnh_activity_detail"))
        self.wait_after_export = int(self.pipeline_config.get("wait_after_export_seconds", 180))
        self.poll_seconds = int(self.pipeline_config.get("poll_seconds", 60))
        self.max_polls_per_date = int(self.pipeline_config.get("max_polls_per_date", 12))
        self.final_polls = int(self.pipeline_config.get("final_polls", 20))

    def run(self) -> None:
        et = self._dimension_et(self.dimension)
        client = QnhClient(
            et=et,
            mtgsig_service_url=self.settings.qnh.mtgsig_service_url,
            request_timeout=int(self.pipeline_config.get("request_timeout_seconds", 60)),
        )
        stores = client.list_stores()
        print(f"{self.dimension.name}: loaded {len(stores)} stores")

        for day in iter_days(self.start, self.end):
            print(f"{self.dimension.name}: exporting {day}")
            self._submit_exports_for_day(client, stores, day)
            print(f"{self.dimension.name}: waiting {self.wait_after_export}s for {day}")
            time.sleep(self.wait_after_export)
            if not self._drain_pending(client, self.max_polls_per_date):
                raise RuntimeError(f"{self.dimension.name}: pending records remain after {day}")

        print(f"{self.dimension.name}: final drain")
        if not self._drain_pending(client, self.final_polls):
            raise RuntimeError(f"{self.dimension.name}: pending records remain after final drain")
        print(f"{self.dimension.name}: complete")

    def _submit_exports_for_day(self, client: QnhClient, stores: list[Store], day: date) -> None:
        with mysql_connection(self.settings.database) as connection:
            repository = StatusRepository(connection)
            for store in stores:
                if repository.has_status_today(self.dimension, store, day):
                    print(f"{self.dimension.name}: skip existing status {day} {store.store_id}")
                    continue
                before = datetime.now()
                time.sleep(3)
                client.submit_export(self.dimension, store, day)
                time.sleep(5)
                after = datetime.now()
                repository.insert_status(self.dimension, store, day, before, after)
                print(f"{self.dimension.name}: submitted {day} {store.store_id}")
                time.sleep(1)

    def _drain_pending(self, client: QnhClient, max_polls: int) -> bool:
        for attempt in range(1, max_polls + 1):
            processed = self._process_pending(client)
            remaining = self._pending_count()
            print(f"{self.dimension.name}: imported {processed}, pending {remaining}")
            if remaining == 0:
                return True
            print(f"{self.dimension.name}: sleep {self.poll_seconds}s ({attempt}/{max_polls})")
            time.sleep(self.poll_seconds)
        return self._pending_count() == 0

    def _process_pending(self, client: QnhClient) -> int:
        tasks = client.list_tasks()
        processed = 0
        with mysql_connection(self.settings.database) as connection:
            repository = StatusRepository(connection)
            importer = ActivityDetailImporter(connection)
            for status in repository.pending_statuses(self.dimension, self.start, self.end):
                task = self._match_task(status, tasks)
                if not task and status.url:
                    task = ExportTask(
                        task_name="cached",
                        executing_state=status.status or "已完成",
                        op_time=None,
                        download_url=status.url,
                    )
                if not task or task.executing_state != "已完成" or not task.download_url:
                    continue
                path = self._download_path(status)
                client.download_excel(task.download_url, path)
                repository.update_downloaded(status, task.executing_state, task.download_url)
                imported = importer.import_excel(self.dimension, path, status)
                repository.mark_imported_and_delete(status)
                processed += 1
                print(f"{self.dimension.name}: imported {imported} rows from {path.name}")
        return processed

    def _pending_count(self) -> int:
        with mysql_connection(self.settings.database) as connection:
            repository = StatusRepository(connection)
            return len(repository.pending_statuses(self.dimension, self.start, self.end))

    def _match_task(self, status: ExportStatus, tasks: list[ExportTask]) -> Optional[ExportTask]:
        start_compact = status.start_date.strftime("%Y%m%d")
        today_compact = datetime.today().strftime("%Y%m%d")
        expected_name = f"{self.dimension.expected_task_prefix}{today_compact}_{start_compact}"
        candidates = [
            task
            for task in tasks
            if task.task_name == expected_name
            and task.op_time
            and status.export_before_time <= task.op_time <= status.export_after_time
        ]
        completed = [task for task in candidates if task.executing_state == "已完成"]
        return (completed or candidates or [None])[0]

    def _download_path(self, status: ExportStatus) -> Path:
        filename = (
            f"{safe_filename(status.store_name)}"
            f"{self.dimension.data_source_name}数据_{status.end_date}.xlsx"
        )
        return self.download_dir / self.dimension.name / filename

    @staticmethod
    def _dimension_et(dimension: DimensionConfig) -> str:
        value = os.getenv(dimension.et_env_name)
        if not value:
            raise RuntimeError(f"Missing login state for {dimension.name}: {dimension.et_env_name}")
        return value


def run_activity_detail(settings: RuntimeSettings, dimension: str, start: str, end: str) -> None:
    pipeline = ActivityDetailPipeline(
        settings=settings,
        dimension_name=dimension,
        start=parse_day(start),
        end=parse_day(end),
    )
    pipeline.run()
