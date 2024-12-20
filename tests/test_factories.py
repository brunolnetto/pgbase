import pytest
from pydantic import ValidationError
from pydantic.networks import AnyUrl

from .conftest import DatasourceSettingsFactory, DatabaseSettingsFactory, create_mocked_data_grid


def test_database_settings_factory():
    """Test the DatabaseSettingsFactory produces valid DatabaseSettings."""
    db_settings = DatabaseSettingsFactory()

    # Validate the attributes of the generated DatabaseSettings instance
    assert db_settings.name.startswith("db")
    assert isinstance(db_settings.uri, AnyUrl)  # Change str to AnyUrl
    assert db_settings.admin_username == "admin"
    assert db_settings.admin_password == "password"
    assert db_settings.default_port == 5432
    assert db_settings.pool_size == 10
    assert db_settings.max_overflow == 5


def test_datasource_settings_factory():
    """Test the DatasourceSettingsFactory produces valid DatasourceSettings."""
    ds_settings = DatasourceSettingsFactory(name="TestDatasource")

    # Validate the attributes of the generated DatasourceSettings instance
    assert ds_settings.name == "TestDatasource"
    assert ds_settings.admin_username == "admin"
    assert ds_settings.admin_password == "password"
    assert ds_settings.connection_timeout == 30
    assert ds_settings.retry_attempts == 3
    assert len(ds_settings.databases) == 2  # Ensure 2 databases are created

    for db in ds_settings.databases:
        assert db.name.startswith("db")  # Each database name should start with 'db'
        assert isinstance(db.uri, AnyUrl)  # Change str to AnyUrl
        assert db.admin_username == "admin"
        assert db.admin_password == "password"
        assert db.default_port == 5432
        assert db.pool_size == 10
        assert db.max_overflow == 5


def test_database_settings_factory_validation():
    """Test that DatabaseSettings raises validation error with invalid inputs."""
    with pytest.raises(ValidationError):
        # Attempt to create DatabaseSettings with an invalid uri
        DatabaseSettingsFactory(uri="invalid_uri")


def test_mocked_data_grid():
    """Test that the mocked DataGrid behaves as expected."""
    data_grid = create_mocked_data_grid()

    # Check that the DataGrid has been initialized correctly
    assert len(data_grid.datasources) == 2  # Ensure there are 2 datasources

    # Check that the disconnect_all method can be called
    data_grid.datasources["ds1"].disconnect_all()
    data_grid.datasources["ds2"].disconnect_all()
    data_grid.datasources["ds1"].disconnect_all.assert_called_once()
    data_grid.datasources["ds2"].disconnect_all.assert_called_once()
