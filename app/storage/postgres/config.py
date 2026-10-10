from __future__ import annotations

import os
from collections.abc import Mapping

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL_ENV = "DATABASE_URL"
POSTGRES_DRIVER = "postgresql+psycopg"


class PostgresConfigurationError(ValueError):
    """Raised when PostgreSQL is not configured explicitly and safely."""


def database_url_from_env(
    environ: Mapping[str, str] | None = None,
) -> URL:
    """Return an explicit PostgreSQL URL without exposing it in errors."""

    values = os.environ if environ is None else environ
    raw_url = values.get(DATABASE_URL_ENV, "").strip()
    if not raw_url:
        raise PostgresConfigurationError(
            f"{DATABASE_URL_ENV} must be set to use PostgreSQL"
        )

    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise PostgresConfigurationError(
            f"{DATABASE_URL_ENV} is not a valid SQLAlchemy URL"
        ) from None

    if url.drivername != POSTGRES_DRIVER:
        raise PostgresConfigurationError(
            f"{DATABASE_URL_ENV} must use the {POSTGRES_DRIVER} driver"
        )
    if not url.database:
        raise PostgresConfigurationError(
            f"{DATABASE_URL_ENV} must name a PostgreSQL database"
        )
    return url


def create_postgres_engine(database_url: URL | None = None) -> Engine:
    """Create a lazy PostgreSQL engine; never choose a fallback backend."""

    url = database_url or database_url_from_env()
    if url.drivername != POSTGRES_DRIVER or not url.database:
        raise PostgresConfigurationError(
            f"PostgreSQL requires a {POSTGRES_DRIVER} URL with a database name"
        )
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory without connecting until a session is used."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
