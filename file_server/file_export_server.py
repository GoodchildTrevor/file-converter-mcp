from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
from pathlib import Path

EXPORT_DIR_ENV = os.getenv("FILE_EXPORT_DIR")
EXPORT_DIR = os.path.realpath((EXPORT_DIR_ENV or "/output").rstrip("/"))
os.makedirs(EXPORT_DIR, exist_ok=True)

app = FastAPI()


@app.get("/files/{folder_name}/{filename}")
async def serve_file(folder_name: str, filename: str):
    if ".." in folder_name or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    file_path = os.path.realpath(os.path.join(EXPORT_DIR, folder_name, filename))
    try:
        Path(file_path).relative_to(EXPORT_DIR)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

app.mount("/files", StaticFiles(directory=EXPORT_DIR), name="files")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9003)
    