from typing import Annotated, Literal

from fastapi import Depends, Request
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Read from environment variables (DATABASE_URL, GO_BASE_URL, ...). Defaults suit local dev."""

    database_url: str = "sqlite:///./golinks.db"
    go_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
