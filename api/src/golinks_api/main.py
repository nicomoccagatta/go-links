from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from golinks_api.db import Base, create_db_engine
from golinks_api.errors import install_error_handlers
from golinks_api.middleware import observe_request
from golinks_api.observability import configure_logging
from golinks_api.routes import router
from golinks_api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        # No migrations yet: create_all is enough until the schema has to evolve (then Alembic).
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Go Links",
        version="0.1.0",
        lifespan=lifespan,
        # Operation IDs become names in the generated TS client: `create_link`, not
        # `create_link_api_links_post`.
        generate_unique_id_function=lambda route: route.name,
    )
    app.state.settings = settings
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)

    app.middleware("http")(observe_request)
    install_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
