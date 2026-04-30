# file-converter-mcp

MCP server for exporting and converting content to DOCX, PPTX, XLSX, PDF, CSV and other formats.

Clean-room rewrite of [mcp-file-converter](https://github.com/GoodchildTrevor/mcp-file-converter)
with a layered architecture.

## Architecture

```
app/          — FastMCP server, config, models, middleware
tools/        — @mcp.tool() thin wrappers (no business logic here)
formats/      — Format renderers: docx, pptx, xlsx, pdf, csv, raw
storage/      — Filesystem: paths, read/write, cleanup
integrations/ — External HTTP clients (OpenWebUI)
```

## Quick start

```bash
cp .env.example .env
# edit .env
docker compose up --build
```

## Available tools

| Tool | Description |
|---|---|
| `export_text_file` | Export text/markdown to txt, md, html, json, xml, docx, pptx, xlsx, pdf |
| `export_document` | Export tabular data to csv, xlsx, docx, pptx |
| `save_file` | Save raw string content to a file |
| `list_files` | List files in the output directory |
| `delete_file` | Delete a generated file |
| `create_archive` | Pack multiple files into zip / tar / tar.gz / 7z |
| `cleanup_old_files` | Remove files older than the configured delay |
| `upload_to_owui` | Upload a file to OpenWebUI |
| `download_from_owui` | Download a file from OpenWebUI |
| `get_version` | Return service version and feature list |
