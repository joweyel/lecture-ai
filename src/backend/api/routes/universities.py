from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from db.session import SessionDep
from models import Universities
from schemas.lectures import UniversityCreate, UniversityRead

router = APIRouter(prefix="/universities", tags=["universities"])


@router.post("", response_model=UniversityRead, status_code=status.HTTP_201_CREATED)
async def create_university(
    session: SessionDep,
    university_create: UniversityCreate,
) -> UniversityRead:
    """Create a new university.

    Universities are shared data with no owner: any user may add one
    and every user sees all of them. The name is globally unique.

    Parameters
    ----------
    session: SessionDep
        The database session.
    university_create: UniversityCreate
        The university to create.

    Returns
    -------
    UniversityRead
        The created university data.
    """
    university = Universities(**university_create.model_dump())
    session.add(university)
    await session.commit()
    await session.refresh(university)
    return university


@router.get("", response_model=list[UniversityRead])
async def list_universities(
    session: SessionDep,
) -> list[UniversityRead]:
    """List all universities.

    Parameters
    ----------
    session: SessionDep
        The database session.

    Returns
    -------
    list[UniversityRead]
        The list of universities.
    """
    stmt = select(Universities).order_by(Universities.name)
    return (await session.scalars(stmt)).all()


@router.get("/{university_id}", response_model=UniversityRead)
async def get_university(
    session: SessionDep,
    university_id: UUID,
) -> UniversityRead:
    """Get a university by ID.

    Parameters
    ----------
    session: SessionDep
        The database session.
    university_id: UUID
        The ID of the university to get.

    Returns
    -------
    UniversityRead
        The university data.
    """
    stmt = select(Universities).where(Universities.id == university_id)
    university = await session.scalar(stmt)
    if not university:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="University not found"
        )
    return university
