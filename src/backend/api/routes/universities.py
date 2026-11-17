from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from api.dependencies import CurrentUserId
from db.session import SessionDep
from models import Universities
from schemas.lectures import UniversityCreate, UniversityRead, UniversityUpdate

router = APIRouter(prefix="/universities", tags=["universities"])


@router.post("", response_model=UniversityRead, status_code=status.HTTP_201_CREATED)
async def create_university(
    session: SessionDep,
    user_id: CurrentUserId,
    university_create: UniversityCreate,
) -> UniversityRead:
    """Create a new university.

    Each user keeps their own list, so the name is unique per user rather
    than globally. Two users may each have a "TU Darmstadt".

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the user.
    university_create: UniversityCreate
        The university to create.

    Returns
    -------
    UniversityRead
        The created university data.
    """
    university = Universities(user_id=user_id, **university_create.model_dump())
    session.add(university)
    await session.commit()
    await session.refresh(university)
    return university


@router.get("", response_model=list[UniversityRead])
async def list_universities(
    session: SessionDep,
    user_id: CurrentUserId,
) -> list[UniversityRead]:
    """List the current user's universities.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the user.

    Returns
    -------
    list[UniversityRead]
        The list of universities.
    """
    stmt = (
        select(Universities)
        .where(Universities.user_id == user_id)
        .order_by(Universities.name)
    )
    return (await session.scalars(stmt)).all()


@router.get("/{university_id}", response_model=UniversityRead)
async def get_university(
    session: SessionDep,
    user_id: CurrentUserId,
    university_id: UUID,
) -> UniversityRead:
    """Get a university by ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the user.
    university_id: UUID
        The ID of the university to get.

    Returns
    -------
    UniversityRead
        The university data.
    """
    stmt = select(Universities).where(
        Universities.user_id == user_id,
        Universities.id == university_id,
    )
    university = await session.scalar(stmt)
    if not university:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="University not found"
        )
    return university


@router.patch("/{university_id}", response_model=UniversityRead)
async def patch_university(
    session: SessionDep,
    user_id: CurrentUserId,
    university_id: UUID,
    university_name: UniversityUpdate,
):
    """Patch a university name.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the user.
    university_id: UUID
        The ID of the university to patch.
    university_name: UniversityUpdate
        The new name of the university.

    Returns
    -------
    UniversityRead
        The updated university.
    """
    stmt = select(Universities).where(
        Universities.user_id == user_id,
        Universities.id == university_id,
    )
    university = await session.scalar(stmt)
    if not university:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="University not found"
        )
    for field, value in university_name.model_dump(exclude_unset=True).items():
        setattr(university, field, value)

    await session.commit()
    await session.refresh(university)
    return university


@router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_university(
    session: SessionDep,
    user_id: CurrentUserId,
    university_id: UUID,
) -> None:
    """Delete a university that no course refers to.

    Parameters
    ----------
    session: SessionDep
        The database session.
    user_id: CurrentUserId
        The ID of the user.
    university_id: UUID
        The ID of the university to delete.

    Returns
    -------
    None
        No content response.
    """
    stmt = select(Universities).where(
        Universities.user_id == user_id,
        Universities.id == university_id,
    )
    university = await session.scalar(stmt)
    if not university:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="University not found"
        )
    await session.delete(university)
    await session.commit()
    return None
