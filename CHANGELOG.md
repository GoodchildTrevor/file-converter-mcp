# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-25

### Added
- `export_text_file` — export text/markdown/HTML/JSON/XML/CSV/DOCX/PPTX/XLSX/PDF via MCP tool
- `export_document` — export two-dimensional tabular data to CSV, XLSX, DOCX, PPTX
- `save_file` — save raw string content to a file
- `list_files` — list files in the output directory
- `delete_file` — delete a generated file by name
- `create_archive` — pack multiple files into ZIP / TAR / TAR.GZ / 7Z
- `cleanup_old_files` — remove files older than the configured delay
- `upload_to_owui` — upload a file to OpenWebUI
- `download_from_owui` — download a file from OpenWebUI
- `get_version` — return service version and feature list
- Bearer token authentication middleware (`MCP_AUTH_TOKEN`)
- Optional DOCX/PPTX style template support via `DOCS_TEMPLATE_PATH`
- Optional OpenWebUI integration via `OWUI_URL` + `JWT_SECRET`
- Automatic file cleanup via `FILES_DELAY` / `PERSISTENT_FILES`
- Docker + Docker Compose support
- Dedicated file server (`file_server/`) for serving generated files over HTTP

### Fixed
- `export_document` with `format="docx"` now renders a proper Word table
  instead of tab-separated plain text
