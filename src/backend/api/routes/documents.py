from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserId
from db.session import SessionDep
from models import Documents
from schemas.document import DocumentCreate, DocumentRead, DocumentUpdate

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
