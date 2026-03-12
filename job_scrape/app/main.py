from fastapi import FastAPI

from app.api.routes.api import router as api_router
from app.core.config import API_PREFIX, DEBUG, PROJECT_NAME, VERSION


def get_application() -> FastAPI:
    application = FastAPI(title=PROJECT_NAME, debug=DEBUG, version=VERSION)
    application.include_router(api_router, prefix=API_PREFIX)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = get_application()
