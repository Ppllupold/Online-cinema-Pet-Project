from fastapi import FastAPI

from src.config.settings import get_settings
from src.routers.stars import router as stars_router
from src.routers.genres import router as genres_router

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
# app.include_router(movies.router, prefix="/api/v1", tags=["Movies"])
app.include_router(stars_router, prefix="/api/v1", tags=["Stars"])
app.include_router(genres_router, prefix="/api/v1", tags=["Genres"])


# Health check
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "message": "Cinema API is running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # auto-reload при змінах коду
    )
