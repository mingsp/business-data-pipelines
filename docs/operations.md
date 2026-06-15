# Operations

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill `.env` with database credentials and the signing-service URL. Do not put `_et` in `.env`;
the job reads the latest QNH cookie payload from `qnh_cookies_data`.

## Manual Backfill

Run dimensions sequentially when both dimensions use the same QNH account:

```powershell
.\scripts\run_qnh_activity_detail_all.ps1 -StartDate 2026-06-04 -EndDate 2026-06-09
```

Use individual scripts only when one dimension needs recovery:

```powershell
.\scripts\run_qnh_activity_detail_activity.ps1 -StartDate 2026-06-04 -EndDate 2026-06-09
.\scripts\run_qnh_activity_detail_store.ps1 -StartDate 2026-06-03 -EndDate 2026-06-09
```

## Daily Scheduling

Create a Windows Task Scheduler task that runs after QNH has finished producing yesterday's data:

Use the sequential wrapper:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts\run_qnh_activity_detail_all.ps1
```

The script writes logs to `logs/`, which is ignored by git.

## Recovery

- If a task fails before import, re-run the same date. Existing status rows for today's submitted
  tasks are reused.
- If import fails after download, re-run the same date. The target-table slice is replaced by
  `date` and `store_id`.
- If the login state expires, refresh the source account through the existing login automation so
  `qnh_cookies_data` receives a fresh row, then re-run the failed date range.
- If QNH rate-limits the account, increase `wait_after_export_seconds` or `poll_seconds` in config.

## Verification Queries

After a run, verify that target tables contain every requested business date and that the active
status queue is empty for the submitted dimensions.

```sql
SELECT date, COUNT(*) FROM activity_detail GROUP BY date ORDER BY date;
SELECT date, COUNT(*) FROM activity_detail_store GROUP BY date ORDER BY date;

SELECT data_source_name, COUNT(*)
FROM qnh_data_export_status_table
WHERE data_source_name IN ('活动明细-活动-活动维度', '活动明细-活动-门店维度')
  AND data_storage_status IS NULL
GROUP BY data_source_name;
```
