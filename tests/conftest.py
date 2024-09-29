import pytest

from pgutils.core import DatabaseConfig, Database, MultiDatabase


@pytest.fixture
def invalid_uri_config():
    return {
        "uri": "invalid_uri",
        "admin_username": "postgres",
        "admin_password": "postgres",
        "async_mode": False,
        "pool_size": 10,
        "max_overflow": 5,
    }

@pytest.fixture
def sync_config():
    return DatabaseConfig(
        uri="postgresql+psycopg://postgres:postgres@localhost:5432/mydatabase",
        admin_username="postgres",
        admin_password="postgres",
        async_mode=False,
        pool_size=10,
        max_overflow=5
    )


@pytest.fixture
def async_config():
    return DatabaseConfig(
        uri="postgresql+asyncpg://postgres:postgres@localhost:5432/mydatabase",
        admin_username="postgres",
        admin_password="postgres",
        async_mode=True,
        pool_size=10,
        max_overflow=5
    )


@pytest.fixture
def sync_database(sync_config):
    db = Database(sync_config)
    yield db
    db.drop_database_if_exists(sync_config.db_name)


@pytest.fixture
def async_database(async_config):
    db = Database(async_config)
    yield db
    db.drop_database_if_exists(async_config.db_name)