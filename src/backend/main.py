from fastapi import FastAPI
from config import settings

app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/")
def home() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_endpoint() -> dict[str, bool]:
    return {"healthy": True}
