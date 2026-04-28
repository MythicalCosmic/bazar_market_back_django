from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from src.app.service.storage_service import resolve_file, save_upload
from src.models.file import UploadResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", response_model=UploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    file_id, size, duplicate = await save_upload(file)
    # url_for builds an absolute URL using the request's host/scheme,
    # so the main backend can store/display whatever we return verbatim.
    url = str(request.url_for("download_file", file_id=file_id))
    return UploadResponse(
        id=file_id,
        url=url,
        filename=file.filename or "",
        content_type=file.content_type or "application/octet-stream",
        size=size,
        duplicate=duplicate,
    )


@router.get("/{file_id}", name="download_file")
async def download_file(file_id: str):
    resolved = resolve_file(file_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path, meta = resolved

    # FileResponse uses the kernel's sendfile() syscall on Linux,
    # so bytes go straight from disk to socket without copying through Python.
    return FileResponse(
        file_path,
        media_type=meta["content_type"],
        filename=meta["filename"],
    )
