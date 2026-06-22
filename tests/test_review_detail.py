from __future__ import annotations

from datetime import date

from business_data_pipelines.pipelines.qnh.review_detail.importer import (
    nullable_int,
    parse_excel_date,
)
from business_data_pipelines.pipelines.qnh.review_detail.pipeline import (
    ReviewDetailPipeline,
    default_date_range,
)


def test_default_date_range_matches_qnh_page_window():
    start, end = default_date_range(today=date(2026, 6, 22), lookback_days=30)

    assert start == date(2026, 5, 24)
    assert end == date(2026, 6, 22)


def test_parse_excel_date_accepts_qnh_export_format():
    assert parse_excel_date("2026.06.21") == date(2026, 6, 21)


def test_nullable_int_keeps_blank_scores_null():
    assert nullable_int("") is None
    assert nullable_int("5") == 5


def test_review_detail_default_filters_match_business_scope():
    pipeline = object.__new__(ReviewDetailPipeline)
    pipeline.start = date(2026, 5, 24)
    pipeline.end = date(2026, 6, 22)
    pipeline.pipeline_config = {"page_size": 10}
    pipeline.is_valid = "1"
    pipeline.comment_level = "BAD_COMMENT"
    pipeline.reply_status_for_page = None

    payload = pipeline._query_payload()

    assert payload["isValid"] == "1"
    assert payload["commentLevel"] == "BAD_COMMENT"
    assert "replyStatusForPage" not in payload
