from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from pymysql.connections import Connection

from business_data_pipelines.core.excel import read_two_row_header_sheet
from business_data_pipelines.core.values import to_decimal, to_int, to_text
from business_data_pipelines.pipelines.qnh.activity_detail.models import DimensionConfig, ExportStatus


class ActivityDetailImporter:
    def __init__(self, connection: Connection):
        self.connection = connection

    def import_excel(self, dimension: DimensionConfig, path: Path, status: ExportStatus) -> int:
        rows = self._parse_rows(dimension, path, status)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM `{dimension.target_table}` WHERE date = %s AND store_id = %s",
                (status.end_date, status.store_id),
            )
            if rows:
                columns = list(rows[0])
                column_sql = ", ".join(f"`{column}`" for column in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.executemany(
                    f"INSERT INTO `{dimension.target_table}` ({column_sql}) VALUES ({placeholders})",
                    [[row[column] for column in columns] for row in rows],
                )
        self.connection.commit()
        return len(rows)

    def _parse_rows(
        self,
        dimension: DimensionConfig,
        path: Path,
        status: ExportStatus,
    ) -> list[dict[str, Any]]:
        source_rows = read_two_row_header_sheet(path, data_start_row=4)
        parsed: list[dict[str, Any]] = []
        for source in source_rows:
            row = self._base_row(source, status.end_date, status.store_id)
            if dimension.has_store_column:
                row["store_name"] = to_text(source.get("门店"))
            else:
                row["store_name"] = status.store_name
            if dimension.has_active_store_count:
                row["active_store_count"] = to_int(source.get("动销门店数"))
            parsed.append(row)
        return parsed

    @staticmethod
    def _base_row(source: dict[str, Any], day: date, store_id: str) -> dict[str, Any]:
        return {
            "date": day,
            "store_id": store_id,
            "store_name": None,
            "activity_id": to_text(source.get("活动ID")),
            "activity_name": to_text(source.get("营销活动")),
            "channel_name": to_text(source.get("渠道名称")),
            "activity_type": to_text(source.get("活动类型")),
            "activity_source": to_text(source.get("活动来源")),
            "activity_order_count": to_int(source.get("活动订单数")),
            "activity_penetration_rate": to_text(source.get("活动渗透率")),
            "activity_order_amount": to_decimal(source.get("活动订单金额")),
            "activity_order_income": to_decimal(source.get("活动订单收入")),
            "merchant_discount": to_decimal(source.get("商家优惠")),
            "platform_subsidy": to_decimal(source.get("平台补贴")),
            "activity_product_count": to_int(source.get("活动商品数")),
            "activity_sales_qty": to_int(source.get("活动销量")),
        }

