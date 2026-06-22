from __future__ import annotations

import json
import time
from datetime import date, datetime
from urllib.parse import urljoin

import requests

from business_data_pipelines.core.http import with_retries
from business_data_pipelines.pipelines.qnh.activity_detail.models import (
    DimensionConfig,
    ExportTask,
    Store,
)


class QnhClient:
    def __init__(self, *, et: str, mtgsig_service_url: str, request_timeout: int = 60):
        self.et = et
        self.mtgsig_service_url = mtgsig_service_url
        self.request_timeout = request_timeout

    @property
    def cookies(self) -> dict[str, str]:
        return {
            "_app_id": "3",
            "_biz_app_id": "2",
            "_et": self.et,
        }

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
        }

    def mtgsig(self, method: str, url: str, params: dict, data: dict) -> str:
        def action() -> str:
            response = requests.post(
                self.mtgsig_service_url,
                headers={"Content-Type": "application/json"},
                json={"method": method, "url": url, "params": params, "data": data},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("mtgsig"), str):
                return payload["mtgsig"]
            if isinstance(payload, str):
                return payload
            raise ValueError(f"unexpected mtgsig response: {payload!r}")

        return with_retries(action, attempts=3, wait_seconds=30, label="mtgsig")

    def signed_post(self, url: str, params: dict, data: dict) -> dict:
        headers = self.headers
        headers["mtgsig"] = self.mtgsig("POST", url, params, data)
        response = requests.post(
            url,
            headers=headers,
            cookies=self.cookies,
            params=params,
            data=json.dumps(data, separators=(",", ":")),
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    def list_stores(self) -> list[Store]:
        url = "https://qnh.meituan.com/api/v1/common/poi/queryCityPoiListWithPermission"
        params = {"yodaReady": "h5", "csecplatform": "4", "csecversion": "3.2.0"}
        data = {"entityTypes": [3, 6], "excludeWarehouseBindingStore": True}

        def action() -> list[Store]:
            payload = self.signed_post(url, params, data)
            if "data" not in payload:
                raise ValueError(f"store list missing data: {payload!r}")
            stores: list[Store] = []
            for city in payload["data"]:
                for poi in city.get("poiList", []):
                    stores.append(Store(store_id=str(poi["poiId"]), store_name=poi["poiName"]))
            return stores

        return with_retries(action, attempts=3, wait_seconds=30, label="store list")

    def submit_export(self, dimension: DimensionConfig, store: Store, day: date) -> dict:
        url = "https://qnh.meituan.com/goldengateway/empower/generic/table/download"
        params = {"yodaReady": "h5", "csecplatform": "4", "csecversion": "4.1.1"}
        yyyymmdd = day.strftime("%Y%m%d")
        data = {
            "viewCode": dimension.view_code,
            "param": {
                "activity": {"activity": []},
                "activityId": "",
                "activityName": "",
                "category": {"categoryType": 2, "value": []},
                "poiIds": [store.store_id],
                "startDate": yyyymmdd,
                "endDate": yyyymmdd,
                "dateType": "d",
                "categoryType": 2,
                "page": 1,
                "pageSize": 10,
                "hasMore": True,
                "selectedDataCodes": dimension.selected_data_codes,
                "channels": [],
                "activityType": None,
                "order": "act_ord_cnt desc",
                "firstCategoryIds": [],
                "secondCategoryIds": [],
                "thirdCategoryIds": [],
            },
        }

        def action() -> dict:
            return self.signed_post(url, params, data)

        return with_retries(action, attempts=3, wait_seconds=30, label="submit export")

    def list_tasks(self) -> list[ExportTask]:
        url = "https://qnh.meituan.com/api/v1/task/queryTasks"
        params = {"yodaReady": "h5", "csecplatform": "4", "csecversion": "4.1.1"}
        display_date = datetime.now().strftime("%Y.%m.%d")
        compact_date = datetime.now().strftime("%Y%m%d")
        tasks: list[ExportTask] = []
        page = 1
        page_size = 50

        while True:
            data = {
                "queryType": "TAB_DOWNLOAD",
                "date": [display_date, display_date],
                "pageSize": page_size,
                "_t": int(time.time() * 1000),
                "startTime": compact_date,
                "endTime": compact_date,
                "page": page,
                "taskMode": "",
            }
            payload = self.signed_post(url, params, data)
            if not payload.get("success"):
                raise RuntimeError(f"query task failed: {payload.get('msg')}")
            task_data = payload.get("data", {})
            for task in task_data.get("list", []):
                op_time = None
                if task.get("opTime"):
                    op_time = datetime.strptime(task["opTime"].replace(".", "-", 2), "%Y-%m-%d %H:%M:%S")
                link = task.get("oprLinkUrl")
                if link and not link.startswith("http"):
                    link = urljoin("https://qnh.meituan.com", link)
                tasks.append(
                    ExportTask(
                        task_name=task.get("taskName"),
                        executing_state=task.get("executingState"),
                        op_time=op_time,
                        download_url=link,
                    )
                )
            total = task_data.get("total", 0)
            if page * page_size >= total:
                return tasks
            page += 1
            time.sleep(1)

    def download_excel(self, url: str, destination) -> None:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {self.et}", "User-Agent": "Mozilla/5.0"},
            stream=True,
            timeout=180,
        )
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as file:
            for chunk in response.iter_content(8192):
                file.write(chunk)

    def download_public_file(self, url: str, destination) -> None:
        response = requests.get(
            url,
            headers={
                "Referer": "https://qnh.meituan.com/",
                "User-Agent": self.headers["User-Agent"],
            },
            stream=True,
            timeout=180,
        )
        response.raise_for_status()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as file:
            for chunk in response.iter_content(8192):
                file.write(chunk)
