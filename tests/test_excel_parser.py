from __future__ import annotations

import os

from openpyxl import Workbook

from business_data_pipelines.core.config import load_dotenv
from business_data_pipelines.core.excel import read_two_row_header_sheet


def test_read_two_row_header_sheet_prefers_second_header_row(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "基础信息"
    sheet["A2"] = "活动ID"
    sheet["B1"] = "指标"
    sheet["B2"] = "活动订单数"
    sheet["A3"] = "汇总"
    sheet["B3"] = 99
    sheet["A4"] = "A100"
    sheet["B4"] = 12
    path = tmp_path / "sample.xlsx"
    workbook.save(path)

    rows = read_two_row_header_sheet(path, data_start_row=4)

    assert rows == [{"活动ID": "A100", "活动订单数": 12}]


def test_load_dotenv_accepts_utf8_bom(tmp_path):
    path = tmp_path / ".env"
    path.write_text("\ufeffBDP_TEST_KEY=value\n", encoding="utf-8")

    load_dotenv(path)

    assert os.getenv("BDP_TEST_KEY") == "value"
