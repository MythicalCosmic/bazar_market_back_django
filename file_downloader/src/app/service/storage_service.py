import hashlib
import json
import secrets
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import UploadFile

from src.config.config import STORAGE_DIR, TMP_DIR

# 1 MiB chunks — large enough to amortize syscall overhead, small enough
# that we never hold a big upload fully in memory.
CHUNK_SIZE = 1024 * 1024


async def save_upload(upload_file: UploadFile) -> tuple[str, int, bool]:
    """Stream an upload to disk while computing its sha256.

    The sha256 hex digest doubles as the file id, which gives us free
    content-addressed deduplication: identical bytes always land at the
    same path, so a re-upload just collapses onto the existing blob.

    Returns: (file_id, size_in_bytes, was_duplicate)
    """
    hasher = hashlib.sha256()
    size = 0

    # Random temp name so concurrent uploads of the same content don't
    # fight over the same temp file before we know the final hash.
    tmp_path = TMP_DIR / secrets.token_hex(16)

    async with aiofiles.open(tmp_path, "wb") as f:
        while chunk := await upload_file.read(CHUNK_SIZE):
            hasher.update(chunk)
            size += len(chunk)
            await f.write(chunk)

    file_id = hasher.hexdigest()
    final_path = STORAGE_DIR / file_id

    if final_path.exists():
        # Same bytes already stored — discard the temp copy and report dup.
        await aiofiles.os.remove(tmp_path)
        return file_id, size, True

    # Atomic rename into the content-addressed slot. On POSIX this is a
    # single inode swap, so even if two requests upload the same new file
    # in parallel the second rename simply overwrites with identical bytes.
    await aiofiles.os.rename(tmp_path, final_path)

    # Sidecar metadata so the GET endpoint can serve with the original
    # filename and content-type instead of generic octet-stream.
    meta_path = STORAGE_DIR / f"{file_id}.json"
    meta = {
        "filename": upload_file.filename or file_id,
        "content_type": upload_file.content_type or "application/octet-stream",
        "size": size,
    }
    async with aiofiles.open(meta_path, "w") as f:
        await f.write(json.dumps(meta))

    return file_id, size, False


def resolve_file(file_id: str) -> tuple[Path, dict] | None:
    """Look up a stored file by id.

    Returns (file_path, metadata_dict) or None if not found / invalid id.
    The id format check also doubles as path-traversal protection: only
    64-char lowercase hex passes, so '../etc/passwd' can never resolve.
    """
    if len(file_id) != 64 or not all(c in "0123456789abcdef" for c in file_id):
        return None

    file_path = STORAGE_DIR / file_id
    if not file_path.exists():
        return None

    meta_path = STORAGE_DIR / f"{file_id}.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {"filename": file_id, "content_type": "application/octet-stream"}

    return file_path, meta
