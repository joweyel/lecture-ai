from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_endpoint() -> dict[str, bool]:
    return {"healthy": True}
