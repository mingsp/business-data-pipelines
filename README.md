# Business Data Pipelines

Unattended data collection jobs for business reporting platforms.

The repository is organized for multiple future data domains. Each domain lives under
`src/business_data_pipelines/pipelines/<platform>/<business_area>/`, while shared
database, configuration, HTTP, and Excel helpers live under `core`.

## Included Pipeline

- `qnh.activity_detail`
  - Activity dimension: imports to `activity_detail`
  - Store dimension: imports to `activity_detail_store`
  - Reads the latest QNH `_et` from `qnh_cookies_data`.
  - Runs one store at a time inside each account.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill `.env`, then run:

```powershell
bdp qnh activity-detail --dimension activity --start 2026-06-04 --end 2026-06-09 --config config/qnh_activity_detail.example.yaml
bdp qnh activity-detail --dimension store --start 2026-06-03 --end 2026-06-09 --config config/qnh_activity_detail.example.yaml
```

When no date is provided, the command imports yesterday's data. This is the default mode for
Windows Task Scheduler:

```powershell
.\scripts\run_qnh_activity_detail_all.ps1
```

For unattended operation, use Windows Task Scheduler with the scripts in `scripts/`.
When one shared QNH account is used, run dimensions sequentially.

## Documentation

- `docs/architecture.md`: project layout and extension rules.
- `docs/qnh_activity_detail.md`: current QNH activity detail pipeline.
- `docs/operations.md`: deployment, scheduling, and troubleshooting.

## Secrets

Do not commit database credentials, signing-service URLs, Excel exports, logs, or copied cookie
payloads. The repository contains only examples and code. QNH login state is read from the
database at runtime.
