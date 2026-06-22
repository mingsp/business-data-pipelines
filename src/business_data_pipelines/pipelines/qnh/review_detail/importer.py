from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from pymysql.connections import Connection

from business_data_pipelines.core.excel import read_single_row_header_sheet
from business_data_pipelines.core.values import to_int, to_text


TARGET_TABLE = "store_comment_details"


def nullable_int(value: Any) -> int | None:
    text = to_text(value)
    if text in {None, ""}:
        return None
    return to_int(text)


def parse_excel_date(value: Any) -> date | None:
    text = to_text(value)
    if text in {None, ""}:
        return None
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, (int, float, Decimal)):
        number = float(value)
        if number > 0:
            try:
                import xlrd

                return xlrd.xldate_as_datetime(number, 0).date()
            except Exception:
                return None
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


ColumnParser = Callable[[Any], Any]


EXCEL_COLUMNS: list[tuple[str, str, ColumnParser]] = [
    ("渠道", "channel_name", to_text),
    ("门店编码", "store_code", to_text),
    ("门店名称", "store_name", to_text),
    ("订单号", "order_no", to_text),
    ("评价ID", "comment_id", to_text),
    ("订单商品", "order_products", to_text),
    ("订单是否系统匹配", "order_system_matched", to_text),
    ("订单评分", "order_score", nullable_int),
    ("商品评分", "product_score", nullable_int),
    ("包装评分", "packing_score", nullable_int),
    ("配送评分", "delivery_score", nullable_int),
    ("用户评价内容", "user_comment_content", to_text),
    ("商品评价内容", "product_comment_content", to_text),
    ("商品标签", "product_tags", to_text),
    ("踩商品", "negative_products", to_text),
    ("赞商品", "positive_products", to_text),
    ("配送评价内容", "delivery_comment_content", to_text),
    ("配送标签", "delivery_tags", to_text),
    ("评价时间", "comment_date", parse_excel_date),
    ("商家回复", "merchant_reply", to_text),
    ("用户追评", "user_follow_up", to_text),
    ("追评时间", "follow_up_date", parse_excel_date),
    ("评价图片", "comment_images", to_text),
    ("评价状态", "comment_status", to_text),
]


class ReviewDetailImporter:
    def __init__(self, connection: Connection, *, target_table: str = TARGET_TABLE):
        self.connection = connection
        self.target_table = target_table

    def ensure_table(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(self._create_table_sql())
        self.connection.commit()

    def import_excel(self, path: Path, *, start: date, end: date) -> int:
        self.ensure_table()
        rows = self._parse_rows(path, start=start, end=end)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE FROM `{self.target_table}`
                WHERE (`comment_date` BETWEEN %s AND %s)
                   OR (`comment_date` IS NULL AND `export_start_date` = %s AND `export_end_date` = %s)
                """,
                (start, end, start, end),
            )
            if rows:
                columns = list(rows[0])
                column_sql = ", ".join(f"`{column}`" for column in columns)
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.executemany(
                    f"INSERT INTO `{self.target_table}` ({column_sql}) VALUES ({placeholders})",
                    [[row[column] for column in columns] for row in rows],
                )
        self.connection.commit()
        return len(rows)

    def count_rows(self, *, start: date, end: date) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS row_count
                FROM `{self.target_table}`
                WHERE `comment_date` BETWEEN %s AND %s
                """,
                (start, end),
            )
            row = cursor.fetchone()
        return int(row["row_count"] if row else 0)

    def _parse_rows(self, path: Path, *, start: date, end: date) -> list[dict[str, Any]]:
        headers, source_rows = read_single_row_header_sheet(path)
        expected_headers = [column[0] for column in EXCEL_COLUMNS]
        if headers != expected_headers:
            raise RuntimeError(
                "Review detail Excel headers changed. "
                f"expected={expected_headers!r}, actual={headers!r}"
            )

        rows: list[dict[str, Any]] = []
        for source in source_rows:
            row: dict[str, Any] = {
                "export_start_date": start,
                "export_end_date": end,
            }
            for header, column, parser in EXCEL_COLUMNS:
                row[column] = parser(source.get(header))
            row["source_file_name"] = path.name
            rows.append(row)
        return rows

    def _create_table_sql(self) -> str:
        return f"""
        CREATE TABLE IF NOT EXISTS `{self.target_table}` (
          `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '自增ID',
          `export_start_date` DATE NOT NULL COMMENT '导出开始日期',
          `export_end_date` DATE NOT NULL COMMENT '导出结束日期',
          `channel_name` VARCHAR(32) DEFAULT NULL COMMENT '渠道',
          `store_code` VARCHAR(32) DEFAULT NULL COMMENT '门店编码',
          `store_name` VARCHAR(128) DEFAULT NULL COMMENT '门店名称',
          `order_no` VARCHAR(64) DEFAULT NULL COMMENT '订单号',
          `comment_id` VARCHAR(64) DEFAULT NULL COMMENT '评价ID',
          `order_products` TEXT DEFAULT NULL COMMENT '订单商品',
          `order_system_matched` VARCHAR(8) DEFAULT NULL COMMENT '订单是否系统匹配',
          `order_score` TINYINT UNSIGNED DEFAULT NULL COMMENT '订单评分',
          `product_score` TINYINT UNSIGNED DEFAULT NULL COMMENT '商品评分',
          `packing_score` TINYINT UNSIGNED DEFAULT NULL COMMENT '包装评分',
          `delivery_score` TINYINT UNSIGNED DEFAULT NULL COMMENT '配送评分',
          `user_comment_content` TEXT DEFAULT NULL COMMENT '用户评价内容',
          `product_comment_content` TEXT DEFAULT NULL COMMENT '商品评价内容',
          `product_tags` TEXT DEFAULT NULL COMMENT '商品标签',
          `negative_products` TEXT DEFAULT NULL COMMENT '踩商品',
          `positive_products` TEXT DEFAULT NULL COMMENT '赞商品',
          `delivery_comment_content` TEXT DEFAULT NULL COMMENT '配送评价内容',
          `delivery_tags` TEXT DEFAULT NULL COMMENT '配送标签',
          `comment_date` DATE DEFAULT NULL COMMENT '评价时间',
          `merchant_reply` TEXT DEFAULT NULL COMMENT '商家回复',
          `user_follow_up` TEXT DEFAULT NULL COMMENT '用户追评',
          `follow_up_date` DATE DEFAULT NULL COMMENT '追评时间',
          `comment_images` MEDIUMTEXT DEFAULT NULL COMMENT '评价图片',
          `comment_status` VARCHAR(16) DEFAULT NULL COMMENT '评价状态',
          `source_file_name` VARCHAR(255) DEFAULT NULL COMMENT '来源文件名',
          `imported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
          PRIMARY KEY (`id`),
          KEY `idx_comment_date` (`comment_date`),
          KEY `idx_store_code` (`store_code`),
          KEY `idx_comment_id` (`comment_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
          COMMENT='牵牛花评价详情表'
        """

