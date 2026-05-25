# file-converter-mcp

> MCP server for exporting and converting content to DOCX, PPTX, XLSX, PDF, CSV, and other formats.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](Dockerfile)

## Overview

`file-converter-mcp` is a [FastMCP](https://github.com/jlowin/fastmcp) server that gives AI assistants (Claude, OpenWebUI, etc.) the ability to generate real files — Word documents, PowerPoint presentations, Excel spreadsheets, PDFs, CSVs, and archives — and serve them over HTTP.

## Architecture

```
app/          — FastMCP server, config, models, middleware
tools/        — @mcp.tool() thin wrappers (no business logic here)
formats/      — Format renderers: docx, pptx, xlsx, pdf, csv, raw
storage/      — Filesystem: paths, read/write, cleanup
file_server/  — Static HTTP file server for serving generated files
integrations/ — External HTTP clients (OpenWebUI)
templates/    — Optional DOCX/PPTX style templates
```

## Quick Start

**Requirements:** Docker and Docker Compose.

```bash
# 1. Clone the repository
git clone https://github.com/GoodchildTrevor/file-converter-mcp.git
cd file-converter-mcp

# 2. Create your .env file
cp .env.example .env

# 3. Edit .env — set at minimum MCP_AUTH_TOKEN
nano .env

# 4. Start the service
docker compose up --build
```

The MCP server will be available at `http://localhost:9000` and the file server at `http://localhost:9003`.

## Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and edit as needed.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCP_AUTH_TOKEN` | **Yes** | — | Bearer token for authenticating MCP requests. Set to a strong random value. |
| `FILE_EXPORT_DIR` | No | `/output` | Directory inside the container where generated files are stored. |
| `FILE_EXPORT_BASE_URL` | No | `http://localhost:9003/files` | Public base URL used to construct download links returned by tools. |
| `DOCS_TEMPLATE_PATH` | No | _(empty)_ | Path to a `.docx` or `.pptx` file used as a style template for generated documents. |
| `OWUI_URL` | No | _(empty)_ | Base URL of your OpenWebUI instance (e.g. `http://openwebui:3000`). Required for `upload_to_owui` / `download_from_owui`. |
| `JWT_SECRET` | No | _(empty)_ | JWT secret used to authenticate with OpenWebUI. Required if `OWUI_URL` is set. |
| `FILES_DELAY` | No | `3600` | Seconds after which generated files are deleted by `cleanup_old_files`. Set to `0` to keep files forever. |
| `PERSISTENT_FILES` | No | `false` | When `true`, files are never deleted regardless of `FILES_DELAY`. |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

## Available Tools

| Tool | Description |
|---|---|
| `export_text_file` | Export text/markdown to txt, md, html, json, xml, docx, pptx, xlsx, pdf |
| `export_document` | Export tabular data (list of rows) to csv, xlsx, docx, pptx |
| `save_file` | Save raw string content to a file |
| `list_files` | List files in the output directory |
| `delete_file` | Delete a generated file |
| `create_archive` | Pack multiple files into zip / tar / tar.gz / 7z |
| `cleanup_old_files` | Remove files older than the configured delay |
| `upload_to_owui` | Upload a file to OpenWebUI |
| `download_from_owui` | Download a file from OpenWebUI |
| `get_version` | Return service version and feature list |

## Connecting to an MCP Client

Add the following to your MCP client configuration (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "file-converter": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_AUTH_TOKEN"
      }
    }
  }
}
```

Replace `YOUR_MCP_AUTH_TOKEN` with the value you set in `.env`.

## DOCX / PPTX Style Templates

You can supply a `.docx` file as a style template. The service will strip its content but keep all style definitions (fonts, heading styles, etc.), then apply them to generated documents.

Set the path in `.env`:
```
DOCS_TEMPLATE_PATH=/templates/my-template.docx
```

Mount the file in `docker-compose.yaml` if needed:
```yaml
volumes:
  - ./templates:/templates:ro
```

## License

[GNU General Public License v3.0](LICENSE)
