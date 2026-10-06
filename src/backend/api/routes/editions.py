from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserId
from db.session import SessionDep
from models import Courses, LectureEditions
from schemas.lectures import LectureEditionsRead

router = APIRouter(prefix="/editions", tags=["editions"])


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
