from __future__ import annotations

from fastapi import FastAPI

from .protected_routes import router
from .x402_integration import X402IntegrationError, install_x402


def create_app() -> FastAPI:
    app = FastAPI(title="Provider API", version="0.1.0")

    mode = "disabled"
    try:
        mode = install_x402(app)
    except X402IntegrationError as exc:
        # Keep service bootable, but expose explicit status and fail protected route requests in strict mode.
        @app.middleware("http")
        async def strict_gate(request, call_next):
            if request.url.path.startswith("/api/"):
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=500, content={"error": str(exc)})
            return await call_next(request)

    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "x402_mode": mode}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("provider_api.server:app", host="0.0.0.0", port=4000, reload=False)


if __name__ == "__main__":
    main()
