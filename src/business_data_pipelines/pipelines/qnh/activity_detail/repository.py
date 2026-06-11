from __future__ import annotations

from datetime import date, datetime

from pymysql.connections import Connection

from business_data_pipelines.pipelines.qnh.activity_detail.models import (
    DimensionConfig,
    ExportStatus,
    Store,
)


class StatusRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def has_status_today(self, dimension: DimensionConfig, store: Store, day: date) -> bool:
        today = datetime.today().date()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM qnh_data_export_status_table
                WHERE data_source_name = %s
                  AND store_id = %s
                  AND start_date = %s
                  AND DATE(createTime) = %s
                """,
                (dimension.data_source_name, store.store_id, day, today),
            )
            row = cursor.fetchone()
            return bool(row and row["count"])

    def insert_status(
        self,
        dimension: DimensionConfig,
        store: Store,
        day: date,
        export_before_time: datetime,
        export_after_time: datetime,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO qnh_data_export_status_table
                (taskName, data_source_name, store_id, store, start_date, end_date,
                 createTime, export_before_time, export_after_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "活动明细导出",
                    dimension.data_source_name,
                    store.store_id,
                    store.store_name,
                    day,
                    day,
                    datetime.now(),
                    export_before_time,
                    export_after_time,
                ),
            )
        self.connection.commit()

    def pending_statuses(self, dimension: DimensionConfig, start: date, end: date) -> list[ExportStatus]:
        today = datetime.today().date()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT data_source_name, store_id, store, start_date, end_date, createTime,
                       export_before_time, export_after_time, status, url
                FROM qnh_data_export_status_table
                WHERE data_source_name = %s
                  AND data_storage_status IS NULL
                  AND DATE(createTime) = %s
                  AND start_date BETWEEN %s AND %s
                ORDER BY createTime
                """,
                (dimension.data_source_name, today, start, end),
            )
            rows = cursor.fetchall()
        return [
            ExportStatus(
                data_source_name=row["data_source_name"],
                store_id=row["store_id"],
                store_name=row["store"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                create_time=row["createTime"],
                export_before_time=row["export_before_time"],
                export_after_time=row["export_after_time"],
                status=row["status"],
                url=row["url"],
            )
            for row in rows
        ]

    def update_downloaded(self, status: ExportStatus, executing_state: str, url: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE qnh_data_export_status_table
                SET status = %s, url = %s
                WHERE data_source_name = %s
                  AND store_id = %s
                  AND store = %s
                  AND start_date = %s
                  AND end_date = %s
                  AND createTime = %s
                """,
                (
                    executing_state,
                    url,
                    status.data_source_name,
                    status.store_id,
                    status.store_name,
                    status.start_date,
                    status.end_date,
                    status.create_time,
                ),
            )
        self.connection.commit()

    def mark_imported_and_delete(self, status: ExportStatus) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE qnh_data_export_status_table
                SET data_storage_status = %s, data_storage_time = %s
                WHERE data_source_name = %s
                  AND store_id = %s
                  AND store = %s
                  AND start_date = %s
                  AND end_date = %s
                  AND createTime = %s
                """,
                (
                    "入库成功",
                    datetime.now(),
                    status.data_source_name,
                    status.store_id,
                    status.store_name,
                    status.start_date,
                    status.end_date,
                    status.create_time,
                ),
            )
            cursor.execute(
                """
                DELETE FROM qnh_data_export_status_table
                WHERE data_source_name = %s
                  AND store_id = %s
                  AND store = %s
                  AND start_date = %s
                  AND end_date = %s
                  AND createTime = %s
                """,
                (
                    status.data_source_name,
                    status.store_id,
                    status.store_name,
                    status.start_date,
                    status.end_date,
                    status.create_time,
                ),
            )
        self.connection.commit()

