"""Entry point do backend FastAPI do Banco Ágil."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, chat, credit, exchange, interview


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API do assistente virtual do Banco Ágil.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(credit.router, prefix="/api", tags=["credit"])
    app.include_router(interview.router, prefix="/api", tags=["interview"])
    app.include_router(exchange.router, prefix="/api", tags=["exchange"])

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        """Verificação de saúde da API."""
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()