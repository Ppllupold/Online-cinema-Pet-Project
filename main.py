from fastapi import FastAPI

from src.config.settings import get_settings
from src.routers.stars import router as stars_router
from src.routers.genres import router as genres_router
from src.routers.movies import router as movies_router
from src.routers.orders import router as orders_router
from src.routers.shopping import router as shopping_router
from src.routers.accounts import router as accounts_router
from src.routers.payments import router as payments_router
from src.routers.webhooks import router as webhooks_router


settings = get_settings()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
app.include_router(stars_router, prefix="/api/v1", tags=["Stars"])
app.include_router(genres_router, prefix="/api/v1", tags=["Genres"])
app.include_router(movies_router, prefix="/api/v1", tags=["Movies"])
app.include_router(orders_router, prefix="/api/v1", tags=["Orders"])
app.include_router(shopping_router, prefix="/api/v1", tags=["Shopping"])
app.include_router(accounts_router, prefix="/api/v1", tags=["Accounts"])
app.include_router(payments_router, prefix="/api/v1", tags=["Payments"])
app.include_router(webhooks_router, prefix="/api/v1", tags=["Webhooks"])


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
