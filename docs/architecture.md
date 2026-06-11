# Architecture

This project is a long-running home for unattended business data pipelines.

## Directory Rules

- `src/business_data_pipelines/core`: shared utilities only. Keep it platform-neutral.
- `src/business_data_pipelines/pipelines/<platform>/<business_area>`: one business pipeline per
  folder. Each pipeline owns its API client, importer, status handling, and field mapping.
- `config`: safe example YAML files. Real environment values stay outside git.
- `scripts`: operational entrypoints for Windows Task Scheduler or manual backfill.
- `docs`: runbooks and request-capture notes.
- `tests`: parser, importer, and idempotency tests.

## Pipeline Contract

Every production pipeline should provide:

- A CLI command under `bdp`.
- A safe example config file.
- A database import path that is idempotent for the same business date and scope.
- Logs that include date, dimension, store id, submitted task count, imported row count, and errors.
- Secret-free documentation for login state, request capture, scheduling, and recovery.

## Request Capture Model

Browser DevTools or CDP is used only to discover the request contract. The unattended job should
not depend on Codex, DevTools, or a manually-opened browser.

Capture and encode these pieces in code:

- HTTP method and URL.
- Query parameters.
- Required cookies or login token names.
- Headers that affect authentication, signing, or content type.
- JSON request body, especially date, store, dimension, pagination, and selected metric fields.
- Signing flow such as `mtgsig`.
- Task polling endpoint and matching rules.
- Download URL and Excel import mapping.

Never commit captured cookies, login tokens, or internal credentials.
