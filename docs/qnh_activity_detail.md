# QNH Activity Detail Pipeline

This pipeline imports QNH activity detail history into existing database tables.

## Dimensions

| Dimension | Login State | Target Table | Execution Rule |
| --- | --- | --- | --- |
| `activity` | `QNH_ACTIVITY_ET` | `activity_detail` | Sequential by store |
| `store` | `QNH_STORE_ET` | `activity_detail_store` | Sequential by store |

The two dimensions can run at the same time because they use separate login states. Inside each
dimension, exports are submitted one store at a time to reduce account risk.

## Flow

1. Load `.env` and YAML config.
2. Query the store list from QNH.
3. For each business date and store, submit one export task.
4. Insert a status row into `qnh_data_export_status_table`.
5. Poll QNH task center.
6. Match exported tasks by task name and submit time window.
7. Download the Excel file.
8. Delete the existing target-table slice for the same date and store.
9. Import all Excel rows into the existing target table.
10. Mark the status as imported and delete it from `qnh_data_export_status_table`.

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
- `QNH_ACTIVITY_ET`
- `QNH_STORE_ET`
- `QNH_MTGSIG_SERVICE_URL`

Store real values only in `.env` or the scheduler's environment, never in git.
