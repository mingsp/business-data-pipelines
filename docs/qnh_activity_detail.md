# QNH Activity Detail Pipeline

This pipeline imports QNH activity detail history into existing database tables.

## Dimensions

| Dimension | Login State | Target Table | Execution Rule |
| --- | --- | --- | --- |
| `activity` | Latest `_et` from `qnh_cookies_data` | `activity_detail` | Sequential by store |
| `store` | Latest `_et` from `qnh_cookies_data` | `activity_detail_store` | Sequential by store |

The login-state lookup follows the existing XBot package: query the latest row from
`qnh_cookies_data` where `platform = '牵牛花'` and the configured `account` matches, then extract
`_et` from the `cookies` field. The activity and store dimensions can use different configured
accounts, which allows safe parallel execution.

## Flow

1. Load `.env` and YAML config.
2. Read the latest QNH `_et` from `qnh_cookies_data`.
3. Query the store list from QNH.
4. For each business date and store, submit one export task.
5. Insert a status row into `qnh_data_export_status_table`.
6. Poll QNH task center.
7. Match exported tasks by task name and submit time window.
8. Download the Excel file.
9. Delete the existing target-table slice for the same date and store.
10. Import all Excel rows into the existing target table.
11. Mark the status as imported and delete it from `qnh_data_export_status_table`.

## Idempotency

The importer deletes rows from the target table by `date` and `store_id` before inserting the Excel
rows. Re-running the same date and store replaces that slice instead of appending duplicates.

## Date Modes

Backfill:

```powershell
bdp qnh activity-detail --dimension activity --start 2026-06-04 --end 2026-06-09 --config config/qnh_activity_detail.example.yaml
bdp qnh activity-detail --dimension store --start 2026-06-03 --end 2026-06-09 --config config/qnh_activity_detail.example.yaml
```

Daily unattended import for yesterday:

```powershell
bdp qnh activity-detail --dimension activity --config config/qnh_activity_detail.example.yaml
bdp qnh activity-detail --dimension store --config config/qnh_activity_detail.example.yaml
```

Sequential shared-account import:

```powershell
.\scripts\run_qnh_activity_detail_all.ps1
```

Parallel two-account import:

```powershell
.\scripts\run_qnh_activity_detail_parallel.ps1
```

## Required Environment Variables

- `BDP_DB_HOST`
- `BDP_DB_PORT`
- `BDP_DB_NAME`
- `BDP_DB_USER`
- `BDP_DB_PASSWORD`
- `QNH_MTGSIG_SERVICE_URL`

Store database and signing-service values only in `.env` or the scheduler's environment, never in
git. Do not store `_et` in `.env`; it is read from `qnh_cookies_data`.
