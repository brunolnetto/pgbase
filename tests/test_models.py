import pytest
from typing import List, Any
from functools import wraps

from pydantic import ValidationError
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncSession


# Assuming the following imports based on your original code
from pgutils.models import DatabaseSettings, Index, Paginator
from pgutils.constants import (
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_ADMIN_PASSWORD,
)
from .conftest import ASYNC_DB_URL

def test_database_config_valid():
    config = DatabaseSettings(
        uri='postgresql://user:password@localhost:5432/mydatabase',
        admin_username='admin',
        admin_password='strongpassword'
    )
    
    assert config.db_name == 'mydatabase'
    assert str(config.admin_uri) == 'postgresql+psycopg2://admin:***@localhost:5432'
    assert str(config.complete_uri) == 'postgresql://user:***@localhost:5432/mydatabase'

def test_database_config_invalid_uri():
    with pytest.raises(ValidationError) as excinfo:
        DatabaseSettings(
            uri='invalid_uri', admin_username='admin', admin_password='strongpassword'
        )
    assert 'relative URL without a base' in str(excinfo.value)

def test_database_config_invalid_pool_size():
    with pytest.raises(ValidationError) as excinfo:
        DatabaseSettings(
            uri='postgresql://user:password@localhost:5432/mydatabase',
            admin_username='admin',
            admin_password='strongpassword',
            pool_size=-1
        )
    assert 'should be greater than 0' in str(excinfo.value)

def test_database_config_invalid_pool_size():
    with pytest.raises(ValidationError) as excinfo:
        DatabaseSettings(
            uri='mysql://user:password@localhost:5432/mydatabase',
            admin_username='admin',
            admin_password='strongpassword',
            pool_size=1
        )

    assert 'URI must start with' in str(excinfo.value)

def test_database_config_invalid_pool_size():
    with pytest.raises(ValidationError) as excinfo:
        DatabaseSettings(
            uri='postgresql://user:password@localhost:5432/mydatabase',
            admin_username='admin',
            admin_password='strongpassword',
            pool_size=-1
        )

    assert 'should be greater than 0' in str(excinfo.value)


def test_valid_index_btree():
    index = Index(
        table_name='my_table', type='btree', columns=['column1', 'column2']
    )
    assert index.type == 'btree'
    assert index.columns == ['column1', 'column2']
    assert index.expression is None
    assert index.condition is None

def test_invalid_index_btree_duplicate_indexes():
    with pytest.raises(ValidationError) as excinfo:
        Index(
            table_name='my_table', 
            type='btree', 
            columns=['column1', 'column1']
        )

    assert "Index cannot have duplicate columns." in str(excinfo.value)


def test_valid_index_expression():
    index = Index(
        table_name='my_table', 
        type='expression', 
        columns=['column1', 'column2'], 
        expression='column1 + column2'
    )
    assert index.type == 'expression'
    assert index.columns == ['column1', 'column2']
    assert index.expression == 'column1 + column2'

def test_valid_index_partial():
    index = Index(
        table_name='my_table', 
        type='partial', 
        columns=['column1'], 
        condition='column1 IS NOT NULL'
    )
    assert index.type == 'partial'
    assert index.columns == ['column1']
    assert index.condition == 'column1 IS NOT NULL'

def test_invalid_index_type():
    with pytest.raises(ValidationError) as exc_info:
        Index(type='invalid_type', columns=['column1'])
    assert "Index type must be one of" in str(exc_info.value)

def test_columns_must_be_list():
    with pytest.raises(ValidationError) as exc_info:
        Index(
            table_name='my_table', 
            type='btree', 
            columns='not_a_list'
        )
    
    assert "Input should be a valid list" in str(exc_info.value)

def test_expression_required_for_expression_index():
    with pytest.raises(ValidationError) as exc_info:
        Index(
            table_name='my_table', 
            type='expression', 
            columns=['column1']
        )

    assert "Expression index must include 'expression'." in str(exc_info.value)

def test_condition_required_for_partial_index():
    with pytest.raises(ValidationError) as exc_info:
        Index(
            table_name='my_table', 
            type='partial', 
            columns=['column1']
        )
    
    assert "Partial index must include 'condition'." in str(exc_info.value)


def test_table_data_sync(sync_db_engine):
    with sync_db_engine.connect() as conn:
        query=text("SELECT * FROM public.test_table;")
        result = conn.execute(query).fetchall()

        assert len(result) == 4, "Expected 4 rows in test_table."


def test_database_config_validation():
    # Valid case
    valid_config = DatabaseSettings(
        uri="postgresql://postgres:postgres@localhost:5432/mydb",
        admin_username="postgres",
        admin_password="postgres",
        async_mode=True,
    )
    assert valid_config.db_name == 'mydb'
    assert str(valid_config.admin_uri) == "postgresql+psycopg2://postgres:***@localhost:5432"

    # Invalid URI
    with pytest.raises(ValidationError) as exc_info:
        DatabaseSettings(
            uri="invalid_uri",
            admin_username="admin",
            admin_password="strong_password",
        )
    assert "Input should be a valid URL" in str(exc_info.value)


# Test cases for URIs with different schemes
@pytest.mark.parametrize(
    "uri, expect_exception",
    [
        # Invalid schemes (expect exception)
        ("mysql://user:pass@localhost/dbname", True),   # MySQL is not allowed
        ("sqlite://user:pass@localhost/dbname", True),  # SQLite is not allowed
        ("ftp://user:pass@localhost/dbname", True),     # FTP is not allowed
        ("http://user:pass@localhost/dbname", True),    # HTTP is not allowed
        
        # Valid schemes (no exception)
        ("postgresql://user:pass@localhost/dbname", False),         # PostgreSQL standard
        ("postgresql+psycopg://user:pass@localhost/dbname", False), # PostgreSQL with psycopg
        ("postgresql+asyncpg://user:pass@localhost/dbname", False), # PostgreSQL with asyncpg
    ]
)
def test_validate_uri_scheme(uri, expect_exception):
    """Test if the URI scheme validation raises a ValueError for invalid schemes."""
    if expect_exception:
        with pytest.raises(ValueError, match=f"URI must start with"):
            DatabaseSettings(
                uri=uri,
                admin_username=DEFAULT_ADMIN_USERNAME,
                admin_password=DEFAULT_ADMIN_PASSWORD
            )
            

    else:
        # If no exception is expected, the validation should pass, and DatabaseSettings should be created
        settings = DatabaseSettings(
            uri=uri,
            admin_username=DEFAULT_ADMIN_USERNAME,
            admin_password=DEFAULT_ADMIN_PASSWORD
        )
        assert str(settings.uri) == uri


@pytest.mark.asyncio
async def test_async_paginator(async_session_factory):
    # Initialize paginator with a query
    async for async_session in async_session_factory:
        paginator = Paginator(
            async_session, 
            "SELECT * FROM public.test_table",
            batch_size=2
        )

        # Fetch and assert paginated results in batches
        expected_batches = [
            [(1, 'Alice'), (2, 'Bob')],
            [(3, 'Charlie'), (4, 'David')]
        ]

        results = []
        
        async for batch in paginator.paginate():
            results.append(batch)

        # Assert total number of batches
        assert len(results) == len(expected_batches)

        # Assert each batch
        for i, expected_batch in enumerate(expected_batches):
            assert results[i] == expected_batch


@pytest.mark.asyncio
async def test_async_paginator_after_deleting_all_entries(async_session_factory):
    # Initialize paginator with a query
    async for async_session in async_session_factory:
        # Step 1: Delete all entries from the table
        delete_query = text("DELETE FROM test_table")
        await async_session.execute(delete_query)
        await async_session.commit()  # Commit the changes to apply deletion

        # Step 2: Prepare the paginator after deletion
        paginator = Paginator(
            conn=async_session,
            query="SELECT * FROM test_table",
            batch_size=2
        )

        # Step 3: Request the paginator to yield the pages (should yield nothing after deletion)
        async for page in paginator.paginate():
            assert len(page) == 0  # Since we deleted all rows, the page should be empty


def test_paginator(sync_session_factory):
    # Initialize paginator with a query
    session = sync_session_factory()
    paginator = Paginator(
        session, 
        "SELECT * FROM public.test_table",
        batch_size=2
    )

    # Fetch and assert paginated results in batches
    expected_batches = [
        [(1, 'Alice'), (2, 'Bob')],
        [(3, 'Charlie'), (4, 'David')]
    ]

    results = []
    
    for batch in paginator.paginate():
        results.append(batch)

    # Assert total number of batches
    assert len(results) == len(expected_batches)

    # Assert each batch
    for i, expected_batch in enumerate(expected_batches):
        assert results[i] == expected_batch

def test_paginator_with_params(sync_session_factory):
    session = sync_session_factory()
    paginator = Paginator(
        session, 
        "SELECT * FROM public.test_table WHERE name LIKE :name", 
        params={'name': 'A%'}
    )

    # Fetch paginated results
    results = []
    for batch in paginator.paginate():
        results.extend(batch)

    assert len(results) == 1  # Only 'Alice' matches the condition
    assert results[0] == (1, 'Alice')

@pytest.mark.asyncio
async def test_sync_paginator_batches(sync_session_factory):
    session = sync_session_factory()
    paginator = Paginator(
        conn=session,
        query="SELECT * FROM public.test_table",
        batch_size=2
    )

    batches = []
    for batch in paginator.paginate():
        batches.append(batch)

    assert len(batches) == 2  # Should have 2 batches of 2 records
    assert batches[0] == [(1, 'Alice'), (2, 'Bob')]
    assert batches[1] == [(3, 'Charlie'), (4, 'David')]

def test_get_total_count(sync_session_factory):
    session=sync_session_factory()

    # Prepare the paginator
    paginator = Paginator(
        conn=session,
        query="SELECT * FROM test_table",
        batch_size=2
    )
    
    assert paginator._get_total_count() == 4

@pytest.mark.asyncio
async def test_sync_paginator_after_deleting_all_entries(sync_session_factory):
    sync_session: Session = sync_session_factory()
    
    # Step 1: Delete all entries from the table
    delete_query = text("DELETE FROM test_table")
    sync_session.execute(delete_query)
    sync_session.commit()  # Commit the changes to apply deletion

    # Step 2: Prepare the paginator after deletion
    paginator = Paginator(
        conn=sync_session,
        query="SELECT * FROM test_table",
        batch_size=2
    )

    # Step 3: Request the paginator to yield the pages (should yield nothing after deletion)
    for page in paginator.paginate():
        assert len(page) == 0  # Since we deleted all rows, the page should be empty

def test_get_batch_query(sync_session_factory):
    session=sync_session_factory()

    # Prepare the paginator
    paginator = Paginator(
        conn=session,
        query="SELECT * FROM test_table",
        batch_size=2
    )

    # Test the get_batch_query method
    expected_query = "SELECT * FROM test_table LIMIT :limit OFFSET :offset"
    assert paginator._get_batch_query() == expected_query


@pytest.mark.asyncio
async def test_get_total_count_async(async_session_factory):
    async for async_session in async_session_factory:  # Use the session factory
        # Prepare the paginator
        paginator = Paginator(
            conn=async_session,
            query="SELECT * FROM test_table",
            batch_size=2
        )

        # Perform the total count query asynchronously
        total_count = await paginator._get_total_count_async()

        # Assertion to verify the result
        assert total_count == 4

# Example test for db_name property
def test_db_name(sync_settings: DatabaseSettings):
    assert sync_settings.db_name == "db1"



