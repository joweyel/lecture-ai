from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from api.routes import courses, documents, editions, universities
from config import settings
from exceptions import integrity_error_handler

app = FastAPI(title=settings.PROJECT_NAME)

app.add_exception_handler(IntegrityError, integrity_error_handler)

app.include_router(courses.router)
app.include_router(documents.router)
app.include_router(universities.router)
app.include_router(editions.router)


@app.get("/")
def home() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_endpoint() -> dict[str, bool]:
    return {"healthy": True}
