import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from api.routes import courses, documents, editions, language, universities
from api.routes.documents import RUNNING_STATES
from config import settings
from db.session import SessionLocal
from exceptions import integrity_error_handler
from models.document import Documents
from models.enums import IngestionStatus

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Release documents that a previous process left mid-ingestion.

    A background task dies with the process that started it, so a restart
    leaves its document stuck in a running state with nobody working on it.
    Marking those failed lets the user retry.
    """
    async with SessionLocal() as session:
        stmt = (
            update(Documents)
            .where(Documents.status.in_(RUNNING_STATES))
            .values(
                status=IngestionStatus.FAILED,
                error="Ingestion was interrupted by a restart",
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        if result.rowcount:
            logger.warning(
                f"lifespan: released {result.rowcount} document(s) stuck mid-ingestion"
            )

    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_exception_handler(IntegrityError, integrity_error_handler)

app.include_router(courses.router)
app.include_router(documents.router)
app.include_router(universities.router)
app.include_router(editions.router)
app.include_router(language.router)


@app.get("/")
def home() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_endpoint() -> dict[str, bool]:
    return {"healthy": True}
