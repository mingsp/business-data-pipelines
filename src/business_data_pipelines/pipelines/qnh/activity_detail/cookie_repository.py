from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from pymysql.connections import Connection


ET_PATTERN = re.compile(r'_et":\s*"([^"]+)')


@dataclass(frozen=True)
class CookieSource:
    table: str = "qnh_cookies_data"
    platform: str = "牵牛花"
    account: str = "xaypshuxin"


def extract_et(cookies: str) -> str:
    match = ET_PATTERN.search(cookies or "")
    if not match:
        raise RuntimeError("Latest QNH cookies do not contain _et.")
    return match.group(1)


class CookieRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def latest_et(self, source: CookieSource) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT cookies
                FROM `{source.table}`
                WHERE `platform` = %s AND `account` = %s
                ORDER BY `date` DESC
                LIMIT 1
                """,
                (source.platform, source.account),
            )
            row: Optional[dict[str, Any]] = cursor.fetchone()
        if not row or not row.get("cookies"):
            raise RuntimeError(
                f"No QNH cookies found in {source.table} for "
                f"platform={source.platform}, account={source.account}."
            )
        return extract_et(str(row["cookies"]))
