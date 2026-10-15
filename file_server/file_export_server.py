import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("file_export_service")
logging.basicConfig(level=logging.INFO)

EXPORT_DIR_ENV = os.getenv("FILE_EXPORT_DIR")
EXPORT_DIR = os.path.realpath((EXPORT_DIR_ENV or "/output").rstrip("/"))
os.makedirs(EXPORT_DIR, exist_ok=True)

FILE_TTL_DAYS = float(os.getenv("FILE_TTL_DAYS", "7"))
FILE_TTL_SECONDS = FILE_TTL_DAYS * 24 * 60 * 60

CLEANUP_INTERVAL_SECONDS = float(os.getenv("FILE_CLEANUP_INTERVAL_SECONDS", str(6 * 60 * 60)))


def cleanup_expired_files() -> None:
    now = time.time()
    removed_files = 0

    for root, dirs, files in os.walk(EXPORT_DIR, topdown=False):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                continue

            if now - mtime > FILE_TTL_SECONDS:
                try:
                    os.remove(file_path)
                    removed_files += 1
                except OSError as e:
                    logger.warning("Failed to remove expired file %s: %s", file_path, e)

        if root != EXPORT_DIR and not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError:
                pass

    if removed_files:
        logger.info("Cleanup: removed %d expired file(s)", removed_files)


async def cleanup_loop() -> None:
    while True:
        try:
            cleanup_expired_files()
        except Exception as e:  # noqa: BLE001
            logger.error("Cleanup loop error: %s", e)
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(cleanup_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/files/{folder_name}/{filename}")
async def serve_file(folder_name: str, filename: str):
    if ".." in folder_name or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    file_path = os.path.realpath(os.path.join(EXPORT_DIR, folder_name, filename))
    try:
        Path(file_path).relative_to(EXPORT_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    for _ in range(10):
        if os.path.isfile(file_path):
            break
        await asyncio.sleep(0.5)
    else:
        raise HTTPException(status_code=404, detail="File not found")

    encoded = quote(filename, safe="")
    content_disposition = f"attachment; filename*=UTF-8''{encoded}"

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        headers={"Content-Disposition": content_disposition},
    )


app.mount("/files", StaticFiles(directory=EXPORT_DIR), name="files")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9003)
    
