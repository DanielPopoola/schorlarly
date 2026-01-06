from fastapi import FastAPI
from src.config.settings import settings
from src.utils.logger import logger, setup_logger
from src.api.routes.health import health_router


def create_app():
    setup_logger()  # Ensure logger is set up before FastAPI app initialization
    logger.info(f"Starting {settings.APP_NAME} FastAPI application...")

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="AI Academic Writing Agent",
    )

    app.include_router(health_router, prefix="/api")

    @app.on_event("startup")
    async def startup_event():
        logger.info("FastAPI app startup complete.")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("FastAPI app shutdown complete.")

    return app


app = create_app()
