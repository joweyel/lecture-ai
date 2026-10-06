from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserId
from db.session import SessionDep
from models import Courses, LectureEditions
from schemas.lectures import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    LectureEditionsRead,
    LectureEditionsCreate,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    session: SessionDep,
    user_id: CurrentUserId,
    course_create: CourseCreate,
) -> CourseRead:
    """Create a new course.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    course_create: CourseCreate
        The course to create.

    Returns
    -------
    CourseRead
        The created course data.
    """
    course = Courses(**course_create.model_dump(), user_id=user_id)
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course


@router.get("", response_model=list[CourseRead])
async def list_courses(
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[CourseRead]:
    """List all courses.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.

    Returns
    -------
    list[CourseRead]
        The list of courses.
    """
    stmt = select(Courses).where(Courses.user_id == user_id).order_by(Courses.name)
    return (await session.scalars(stmt)).all()


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    session: SessionDep,
    user_id: CurrentUserId,
    course_id: UUID,
) -> CourseRead:
    """Get a course by ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    course_id: UUID
        The ID of the course to get.
    user_id: CurrentUserId
        The ID of the current user.

    Returns
    -------
    CourseRead
        The course data.
    """
    stmt = select(Courses).where(Courses.id == course_id, Courses.user_id == user_id)
    course = await session.scalar(stmt)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    return course


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    session: SessionDep,
    user_id: CurrentUserId,
    course_id: UUID,
    course_update: CourseUpdate,
) -> CourseRead:
    """Update a course.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    course_id: UUID
        The ID of the course to update.
    course_update: CourseUpdate
        The course to update.

    Returns
    -------
    CourseRead
        The updated course data.
    """
    stmt = select(Courses).where(Courses.id == course_id, Courses.user_id == user_id)
    course = await session.scalar(stmt)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    for field, value in course_update.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await session.commit()
    await session.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    session: SessionDep,
    user_id: CurrentUserId,
    course_id: UUID,
) -> None:
    """Delete a course.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    course_id: UUID
        The ID of the course to delete.

    Returns
    -------
    None
    """
    stmt = select(Courses).where(Courses.id == course_id, Courses.user_id == user_id)
    course = await session.scalar(stmt)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    await session.delete(course)
    await session.commit()


@router.get("/{course_id}/editions", response_model=list[LectureEditionsRead])
async def list_editions(
    session: SessionDep,
    user_id: CurrentUserId,
    course_id: UUID,
) -> list[LectureEditionsRead]:
    """List all editions for a course.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    course_id: UUID
        The ID of the course to list editions for.

    Returns
    -------
    list[LectureEditionsRead]
        The list of editions.
    """
    stmt = select(Courses).where(Courses.id == course_id, Courses.user_id == user_id)
    course = await session.scalar(stmt)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    stmt = (
        select(LectureEditions)
        .where(LectureEditions.course_id == course.id)
        .order_by(LectureEditions.year)
    )
    return (await session.scalars(stmt)).all()


@router.post(
    "/{course_id}/editions",
    response_model=LectureEditionsRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_edition(
    session: SessionDep,
    user_id: CurrentUserId,
    course_id: UUID,
    edition_create: LectureEditionsCreate,
) -> LectureEditionsRead:
    """Create a new edition for a course.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the current user.
    course_id: UUID
        The ID of the course to create an edition for.
    edition_create: LectureEditionsCreate
        The edition to create.

    Returns
    -------
    LectureEditionsRead
        The created edition data.
    """
    stmt = select(Courses).where(Courses.id == course_id, Courses.user_id == user_id)
    course = await session.scalar(stmt)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    edition = LectureEditions(**edition_create.model_dump(), course_id=course.id)
    session.add(edition)
    await session.commit()
    await session.refresh(edition)
    return edition
