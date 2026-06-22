from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from business_data_pipelines.core.config import RuntimeSettings
from business_data_pipelines.core.db import mysql_connection
from business_data_pipelines.pipelines.qnh.activity_detail.client import QnhClient
from business_data_pipelines.pipelines.qnh.activity_detail.cookie_repository import (
    CookieRepository,
    CookieSource,
)
from business_data_pipelines.pipelines.qnh.review_detail.importer import (
    TARGET_TABLE,
    ReviewDetailImporter,
)


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def default_date_range(*, today: date | None = None, lookback_days: int = 30) -> tuple[date, date]:
    end = today or date.today()
    return end - timedelta(days=lookback_days - 1), end


class ReviewDetailPipeline:
    def __init__(
        self,
        *,
        settings: RuntimeSettings,
        start: date | None = None,
        end: date | None = None,
    ):
        self.settings = settings
        self.pipeline_config = settings.config.get("qnh_review_detail", {})
        lookback_days = int(self.pipeline_config.get("lookback_days", 30))
        default_start, default_end = default_date_range(lookback_days=lookback_days)
        self.start = start or default_start
        self.end = end or default_end
        self.download_dir = Path(self.pipeline_config.get("download_dir", "downloads/qnh_review_detail"))
        self.target_table = self.pipeline_config.get("target_table", TARGET_TABLE)
        self.export_match_order = bool(self.pipeline_config.get("export_match_order", True))
        self.is_valid = self.pipeline_config.get("is_valid", "1")
        self.comment_level = self.pipeline_config.get("comment_level", "BAD_COMMENT")
        self.reply_status_for_page = self.pipeline_config.get("reply_status_for_page")

    def run(self) -> None:
        et = self._load_et()
        client = QnhClient(
            et=et,
            mtgsig_service_url=self.settings.qnh.mtgsig_service_url,
            request_timeout=int(self.pipeline_config.get("request_timeout_seconds", 120)),
        )
        expected_total = self._query_total(client)
        download_url = self._submit_export(client)
        path = self._download_path()
        client.download_public_file(download_url, path)
        print(
            "review-detail: downloaded "
            f"{urlparse(download_url).netloc}{urlparse(download_url).path} -> {path}"
        )
        with mysql_connection(self.settings.database) as connection:
            importer = ReviewDetailImporter(connection, target_table=self.target_table)
            imported = importer.import_excel(path, start=self.start, end=self.end)
            table_count = importer.count_rows(start=self.start, end=self.end)
        print(
            "review-detail: "
            f"expected_total={expected_total}, imported={imported}, table_count={table_count}"
        )
        if expected_total != imported or imported != table_count:
            raise RuntimeError(
                "Review detail row count mismatch: "
                f"expected_total={expected_total}, imported={imported}, table_count={table_count}"
            )

    def _query_total(self, client: QnhClient) -> int:
        payload = client.signed_post(
            "https://qnh.meituan.com/api/v1/channelComment/queryCommentList",
            self._params(),
            self._query_payload(),
        )
        if not payload.get("success"):
            raise RuntimeError(f"query review detail failed: {payload.get('msg')}")
        data = payload.get("data") or {}
        total = int(data.get("total") or 0)
        print(f"review-detail: query total={total}")
        return total

    def _submit_export(self, client: QnhClient) -> str:
        payload = client.signed_post(
            "https://qnh.meituan.com/api/v1/channelComment/downloadComment",
            self._params(),
            self._export_payload(),
        )
        if not payload.get("success"):
            raise RuntimeError(f"submit review detail export failed: {payload.get('msg')}")
        download_url = ((payload.get("data") or {}).get("downloadUrl") or "").strip()
        if not download_url:
            raise RuntimeError(f"review detail export missing downloadUrl: {payload!r}")
        return download_url

    def _params(self) -> dict[str, str]:
        return {"yodaReady": "h5", "csecplatform": "4", "csecversion": "4.1.1"}

    def _query_payload(self) -> dict:
        payload = {
            "page": 1,
            "pageSize": int(self.pipeline_config.get("page_size", 10)),
            "startTime": self.start.isoformat(),
            "endTime": self.end.isoformat(),
            "poiIds": [],
        }
        return self._with_filters(payload)

    def _export_payload(self) -> dict:
        payload = {
            "poiIds": [],
            "startTime": self.start.isoformat(),
            "endTime": self.end.isoformat(),
            "exportMatchOrder": self.export_match_order,
        }
        return self._with_filters(payload)

    def _with_filters(self, payload: dict) -> dict:
        if self.is_valid:
            payload["isValid"] = self.is_valid
        if self.comment_level:
            payload["commentLevel"] = self.comment_level
        if self.reply_status_for_page:
            payload["replyStatusForPage"] = self.reply_status_for_page
        return payload

    def _download_path(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"qnh_review_detail_{self.start:%Y%m%d}_{self.end:%Y%m%d}_{stamp}.xls"
        return self.download_dir / filename

    def _load_et(self) -> str:
        cookie_config = self.pipeline_config.get("cookie_source", {})
        source = CookieSource(
            table=cookie_config.get("table", "qnh_cookies_data"),
            platform=cookie_config.get("platform", "牵牛花"),
            account=cookie_config.get("account", "xaypshuxin"),
        )
        with mysql_connection(self.settings.database) as connection:
            et = CookieRepository(connection).latest_et(source)
        print(
            "review-detail: loaded login state from "
            f"{source.table}/{source.platform}/{source.account}"
        )
        return et


def run_review_detail(
    settings: RuntimeSettings,
    *,
    start: str | None = None,
    end: str | None = None,
) -> None:
    pipeline = ReviewDetailPipeline(
        settings=settings,
        start=parse_day(start) if start else None,
        end=parse_day(end) if end else None,
    )
    pipeline.run()
