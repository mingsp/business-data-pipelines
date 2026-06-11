from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook


def read_two_row_header_sheet(path: Path, *, data_start_row: int = 4) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=False, data_only=True)
    sheet = workbook.active
    row1 = [sheet.cell(1, col).value for col in range(1, sheet.max_column + 1)]
    row2 = [sheet.cell(2, col).value for col in range(1, sheet.max_column + 1)]
    headers = [row2[i] or row1[i] for i in range(sheet.max_column)]

    records: list[dict[str, Any]] = []
    for row in sheet.iter_rows(min_row=data_start_row, values_only=True):
        if all(value is None for value in row):
            continue
        records.append({headers[i]: row[i] if i < len(row) else None for i in range(len(headers))})
    return records

