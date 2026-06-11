from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

import requests


T = TypeVar("T")


def with_retries(
    action: Callable[[], T],
    *,
    attempts: int,
    wait_seconds: int,
    label: str,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(f"{label} network error, retry {attempt}/{attempts}: {exc}")
        except ValueError as exc:
            last_error = exc
            print(f"{label} parse error, retry {attempt}/{attempts}: {exc}")
        if attempt < attempts:
            time.sleep(wait_seconds)
    if last_error:
        raise last_error
    raise RuntimeError(f"{label} failed")

