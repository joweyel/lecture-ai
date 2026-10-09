from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserId
from db.session import SessionDep
from models import Courses, Documents, LectureDocuments, LectureEditions
from models.enums import MaterialRole
from schemas.lectures import (
    LectureDocumentsCreate,
    LectureDocumentsRead,
    LectureDocumentsUpdate,
    LectureEditionsRead,
    LectureEditionsUpdate,
)

router = APIRouter(prefix="/editions", tags=["editions"])


@router.get("", response_model=list[LectureEditionsRead])
async def list_editions(
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[LectureEditionsRead]:
    """List the editions for the current user's courses.

    Sorted by course name, ascending, then by year, newest first.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.

    Returns
    -------
    list[LectureEditionsRead]
        The editions for the current user's courses.
    """
    stmt = (
        select(LectureEditions)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(Courses.user_id == user_id)
        .order_by(Courses.name, LectureEditions.year.desc())
    )
    return (await session.scalars(stmt)).all()


@router.get("/{edition_id}", response_model=LectureEditionsRead)
async def get_edition(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
) -> LectureEditionsRead:
    """Get an edition by ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition to get.

    Returns
    -------
    LectureEditionsRead
        The edition data.
    """
    stmt = (
        select(LectureEditions)
        .join(Courses, Courses.id == LectureEditions.course_id)  # join on course id
        .where(LectureEditions.id == edition_id, Courses.user_id == user_id)
    )
    edition = await session.scalar(stmt)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )
    return edition


@router.patch("/{edition_id}", response_model=LectureEditionsRead)
async def update_edition(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
    edition_update: LectureEditionsUpdate,
) -> LectureEditionsRead:
    """Update an edition by ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition to update.
    edition_update: LectureEditionsUpdate
        The update data.

    Returns
    -------
    LectureEditionsRead
        The updated edition data.
    """
    stmt = (
        select(LectureEditions)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(LectureEditions.id == edition_id, Courses.user_id == user_id)
    )
    edition = await session.scalar(stmt)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )
    for field, value in edition_update.model_dump(exclude_unset=True).items():
        setattr(edition, field, value)
    await session.commit()
    await session.refresh(edition)
    return edition


@router.delete("/{edition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edition(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
) -> None:
    """Delete an edition by ID.

    The documents themselves survive; only the rows in lecture_documents
    that belong to this edition are removed, by ON DELETE CASCADE.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition to delete.

    Returns
    -------
    None
    """
    stmt = (
        select(LectureEditions)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(LectureEditions.id == edition_id, Courses.user_id == user_id)
    )
    edition = await session.scalar(stmt)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )
    await session.delete(edition)
    await session.commit()


@router.get("/{edition_id}/documents", response_model=list[LectureDocumentsRead])
async def list_edition_documents(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
    role: MaterialRole | None = None,
    week: int | None = None,
) -> list[LectureDocumentsRead]:
    """List the documents added to an edition.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition whose material to list.
    role: MaterialRole | None
        Only return documents with this role.
    week: int | None
        Only return documents for this week.

    Returns
    -------
    list[LectureDocumentsRead]
        The documents of the edition, with their role and week.
    """
    stmt = (
        select(LectureEditions)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(LectureEditions.id == edition_id, Courses.user_id == user_id)
    )
    edition = await session.scalar(stmt)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )
    stmt = select(LectureDocuments).where(LectureDocuments.edition_id == edition_id)
    if role is not None:
        stmt = stmt.where(LectureDocuments.role == role)
    if week is not None:
        stmt = stmt.where(LectureDocuments.week == week)
    stmt = stmt.order_by(LectureDocuments.week, LectureDocuments.role)
    return (await session.scalars(stmt)).all()


@router.put(
    "/{edition_id}/documents/{document_id}", response_model=LectureDocumentsRead
)
async def add_document(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
    document_id: UUID,
    lecture_document_create: LectureDocumentsCreate,
) -> LectureDocumentsRead:
    """Add a document to an edition, or change one already added.

    Both the edition and the document must belong to the current user. Sending
    the same pair again replaces role and week instead of failing on the
    composite primary key.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition to add to.
    document_id: UUID
        The ID of the document to add.
    lecture_document_create: LectureDocumentsCreate
        The role of the document and the week it belongs to.

    Returns
    -------
    LectureDocumentsRead
        The added document, with its role and week.
    """
    stmt = (
        select(LectureEditions)  # SELECT * FROM lecture_editions
        .join(
            Courses, Courses.id == LectureEditions.course_id
        )  # JOIN Courses on Courses.id = LectureEditions.course_id
        .where(
            LectureEditions.id == edition_id,  # WHERE LectureEditions.id = edition_id
            Courses.user_id == user_id,  # AND Courses.user_id = user_id
        )
    )
    edition = await session.scalar(stmt)
    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )
    stmt = select(Documents).where(
        Documents.id == document_id,  # WHERE Documents.id = document_id
        Documents.user_id == user_id,  # AND Documents.user_id = user_id
    )
    document = await session.scalar(stmt)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    stmt = select(LectureDocuments).where(  # SELECT * FROM lecture_documents
        LectureDocuments.edition_id
        == edition_id,  # WHERE LectureDocuments.edition_id = edition_id
        LectureDocuments.document_id
        == document_id,  # AND LectureDocuments.document_id = document_id
    )
    lecture_document = await session.scalar(stmt)
    if lecture_document is None:
        lecture_document = LectureDocuments(
            edition_id=edition_id,
            document_id=document_id,
            **lecture_document_create.model_dump(),
        )
        session.add(lecture_document)
    else:
        for field, value in lecture_document_create.model_dump().items():
            setattr(lecture_document, field, value)
    await session.commit()
    await session.refresh(lecture_document)
    return lecture_document


@router.patch(
    "/{edition_id}/documents/{document_id}", response_model=LectureDocumentsRead
)
async def update_edition_document(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
    document_id: UUID,
    lecture_document_update: LectureDocumentsUpdate,
) -> LectureDocumentsRead:
    """Change the role or the week of a document in an edition.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition the document belongs to.
    document_id: UUID
        The ID of the document.
    lecture_document_update: LectureDocumentsUpdate
        The fields to change.

    Returns
    -------
    LectureDocumentsRead
        The updated document, with its role and week.
    """
    stmt = (
        select(LectureDocuments)
        .join(LectureEditions, LectureEditions.id == LectureDocuments.edition_id)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(
            LectureDocuments.edition_id == edition_id,
            LectureDocuments.document_id == document_id,
            Courses.user_id == user_id,
        )
    )
    lecture_document = await session.scalar(stmt)
    if not lecture_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this edition",
        )
    for field, value in lecture_document_update.model_dump(exclude_unset=True).items():
        setattr(lecture_document, field, value)
    await session.commit()
    await session.refresh(lecture_document)
    return lecture_document


@router.delete(
    "/{edition_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_document(
    session: SessionDep,
    user_id: CurrentUserId,
    edition_id: UUID,
    document_id: UUID,
) -> None:
    """Remove a document from an edition.

    Only the row in lecture_documents is removed. The document is untouched.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    edition_id: UUID
        The ID of the edition the document belongs to.
    document_id: UUID
        The ID of the document.

    Returns
    -------
    None
    """
    stmt = (
        select(LectureDocuments)
        .join(LectureEditions, LectureEditions.id == LectureDocuments.edition_id)
        .join(Courses, Courses.id == LectureEditions.course_id)
        .where(
            LectureDocuments.edition_id == edition_id,
            LectureDocuments.document_id == document_id,
            Courses.user_id == user_id,
        )
    )
    lecture_document = await session.scalar(stmt)
    if not lecture_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in this edition",
        )
    await session.delete(lecture_document)
    await session.commit()
