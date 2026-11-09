from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.dependencies import CurrentUserId
from db.session import SessionDep
from ingestion.extract import ALLOWED_FILE_SUFFIXES
from models.document import Documents
from models.enums import MaterialRole, SourceType
from models.lectures import Courses, LectureDocuments, LectureEditions
from schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from storage import save_upload, target_path

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[DocumentRead]:
    """List the current user's documents, newest first.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.

    Returns
    -------
    list[DocumentRead]
        The list of documents obtained from the database.
    """
    stmt = (  # Get all documents for the current user
        select(Documents)
        .where(Documents.user_id == user_id)
        .order_by(Documents.created_at.desc())
    )
    return (await session.scalars(stmt)).all()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    session: SessionDep,
    user_id: CurrentUserId,
    document_create: DocumentCreate,
) -> DocumentRead:
    """Create a new document.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    document_create: DocumentCreate
        The document to create.

    Returns
    -------
    DocumentRead
        The document obtained from the database.
    """
    document = Documents(**document_create.model_dump(), user_id=user_id)
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@router.post(
    "/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    session: SessionDep,
    user_id: CurrentUserId,
    file: Annotated[UploadFile, File(description="The document to upload")],
    title: Annotated[str, Form(description="The title of the document")],
    source_type: Annotated[SourceType, Form(description="The type of the document")],
    edition_id: Annotated[
        UUID | None, Form(description="Attach the document to this lecture edition")
    ] = None,
    role: Annotated[
        MaterialRole, Form(description="Role of the document in the edition")
    ] = MaterialRole.PRIMARY,
    week: Annotated[
        int | None, Form(ge=1, description="The week of the document")
    ] = None,
) -> DocumentRead:
    """Store an uploaded file and register it. Does not ingest.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    file: UploadFile
        The uploaded file, streamed to disk in blocks so a large book never
        sits in memory.
    title: str
        Display title, a multipart Form field.
    source_type: SourceType
        What kind of material this is, a multipart Form field.
    edition_id: UUID | None
        Attach the document to this lecture edition. Left out for a
        free-standing document.
    role: MaterialRole
        Role within the edition, only used together with `edition_id`.
    week: int | None
        Week within the edition, only used together with `edition_id`.

    Returns
    -------
    DocumentRead
        The new row, at status `pending`. Start the pipeline with
        `POST /documents/{document_id}/ingest`.

    Raises
    ------
    HTTPException
        400 for a missing filename, an unsupported file type or an empty file,
        404 if the edition does not exist or does not belong to the user.
    """
    # Check if filename is provided / not empty
    if file.filename is None or file.filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename"
        )

    # The client controls the filename, so only its suffix is used
    document_id = uuid4()
    suffix: str = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_FILE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix or 'no extension'}",
        )

    target_file_path: Path = target_path(document_id, suffix)

    # If lecture edition was given
    if edition_id is not None:
        lecture_edition = await session.scalar(
            select(LectureEditions)
            .join(Courses)
            .where(LectureEditions.id == edition_id, Courses.user_id == user_id)
        )
        if lecture_edition is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lecture edition not found",
            )
        session.add(
            LectureDocuments(
                edition_id=edition_id,
                document_id=document_id,
                role=role,
                week=week,
            )
        )

    # Write the file, hashing it on the way through
    content_hash, size = await save_upload(file, target_file_path)
    if size == 0:
        target_file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )

    document = Documents(
        id=document_id,
        user_id=user_id,
        title=title,
        source_type=source_type,
        # relative, DOCUMENTS_DIR differs per environment
        file_path=target_file_path.name,
        content_hash=content_hash,
    )
    session.add(document)

    try:
        await session.commit()
    except IntegrityError:
        # A duplicate content_hash becomes a 409 in the global handler, but the
        # file is already saved, so remove it before letting the error through
        target_file_path.unlink(missing_ok=True)
        raise

    await session.refresh(document)
    return document


@router.post(
    "/ingest", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED
)
async def ingest_document(
    session: SessionDep,
    user_id: CurrentUserId,
    document_id: UUID,
    background_tasks: BackgroundTasks,
) -> DocumentRead:
    pass


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    session: SessionDep,
    user_id: CurrentUserId,
    document_id: UUID,
) -> DocumentRead:
    """Get a document by its ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    document_id: UUID
        The ID of the document.

    Returns
    -------
    DocumentRead
        The document obtained from the database.
    """
    stmt = select(Documents).where(
        Documents.user_id == user_id, Documents.id == document_id
    )
    document = await session.scalar(stmt)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    session: SessionDep,
    user_id: CurrentUserId,
    document_id: UUID,
    document_update: DocumentUpdate,
) -> DocumentRead:
    """Change metadata of one document of the current user.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    document_id: UUID
        The ID of the document.
    document_update: DocumentUpdate
        The document to update.

    Returns
    -------
    DocumentRead
        The document obtained from the database.
    """
    stmt = select(Documents).where(
        Documents.user_id == user_id, Documents.id == document_id
    )
    document = await session.scalar(stmt)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    for field, value in document_update.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    await session.commit()
    await session.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    session: SessionDep,
    user_id: CurrentUserId,
    document_id: UUID,
) -> None:
    """Delete a document by its ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    document_id: UUID
        The ID of the document.

    Returns
    -------
    None
        The document is deleted from the database.
    """
    stmt = select(Documents).where(
        Documents.user_id == user_id, Documents.id == document_id
    )
    document = await session.scalar(stmt)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    await session.delete(document)
    await session.commit()
