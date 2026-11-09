"""Where uploaded documents live on disk, and how they get there."""

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from config import settings

UPLOAD_BLOCK_SIZE: int = (
    1 << 20
)  # 1 MiB (1048576 bytes) read buffer, the stdlib uses 64 KiB


def target_path(document_id: UUID, suffix: str) -> Path:
    """Where a new upload goes. The id names the file, the client's name is dropped.

    Parameters
    ----------
    document_id : UUID
        Primary key of the `documents` row the file belongs to.
    suffix : str
        File extension including the dot, already lowercased and validated.

    Returns
    -------
    Path
        The absolute path to write to. The directory is created if missing.
    """
    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DOCUMENTS_DIR / f"{document_id}{suffix}"


def document_path(file_path: str) -> Path:
    """Full path of a stored document, from the bare name kept in the database.

    Parameters
    ----------
    file_path : str
        The value of `documents.file_path`, a file name without a directory.

    Returns
    -------
    Path
        The absolute path inside `settings.DOCUMENTS_DIR`.
    """
    return settings.DOCUMENTS_DIR / file_path


async def save_upload(file: UploadFile, target: Path) -> tuple[str, int]:
    """Stream an upload to `target`, hashing and counting it on the way through.

    Parameters
    ----------
    file : UploadFile
        The uploaded file, read in blocks so a large book never sits in memory.
    target : Path
        Where to write, as returned by `target_path`.

    Returns
    -------
    tuple[str, int]
        The sha256 hex digest for `documents.content_hash`, and the size in
        bytes. A size of 0 means the client sent an empty file.
    """
    digest = hashlib.sha256()
    size = 0
    with target.open("wb") as out:
        while block := await file.read(UPLOAD_BLOCK_SIZE):
            digest.update(block)
            size += len(block)
            out.write(block)
    return digest.hexdigest(), size
