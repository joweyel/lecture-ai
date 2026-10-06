from fastapi import FastAPI
from config import settings

from api.routes import courses, documents, universities, editions

app = FastAPI(title=settings.PROJECT_NAME)

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
