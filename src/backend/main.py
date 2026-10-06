from fastapi import FastAPI
from config import settings

from api.routes import documents

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(documents.router)


@app.get("/")
def home() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_endpoint() -> dict[str, bool]:
    return {"healthy": True}
