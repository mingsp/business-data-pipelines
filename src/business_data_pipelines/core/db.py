from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.connections import Connection

from business_data_pipelines.core.config import DatabaseSettings


@contextmanager
def mysql_connection(settings: DatabaseSettings) -> Iterator[Connection]:
    connection = pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        yield connection
    finally:
        connection.close()

