from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.api import router as api_router
from app.core.config import API_PREFIX, DEBUG, PROJECT_NAME, VERSION


def get_application() -> FastAPI:
    application = FastAPI(title=PROJECT_NAME, debug=DEBUG, version=VERSION)
    application.include_router(api_router, prefix=API_PREFIX)

    @application.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        _request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "meta": None,
                "error": {
                    "code": "VAL_REQUEST_INVALID",
                    "message": "请求参数校验失败",
                    "details": {"errors": exc.errors()},
                },
            },
        )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = get_application()
