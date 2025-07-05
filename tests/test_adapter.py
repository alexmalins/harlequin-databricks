import os
import sys
from collections.abc import Iterator

import pytest
from databricks import sql as databricks_sql
from harlequin.adapter import HarlequinAdapter, HarlequinConnection, HarlequinCursor
from harlequin.catalog import Catalog, CatalogItem
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from textual_fastdatatable.backend import create_backend

from harlequin_databricks.adapter import (
    HarlequinDatabricksAdapter,
    HarlequinDatabricksConnection,
)

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


def test_plugin_discovery() -> None:
    plugin_name = "databricks"
    eps = entry_points(group="harlequin.adapter")
    assert eps[plugin_name]
    adapter_cls = eps[plugin_name].load()
    assert issubclass(adapter_cls, HarlequinAdapter)
    assert adapter_cls == HarlequinDatabricksAdapter


def test_connect() -> None:
    conn = HarlequinDatabricksAdapter(
        server_hostname=os.getenv("DATABRICKS_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        client_id=os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    ).connect()
    assert isinstance(conn, HarlequinConnection)
    conn.close()


def test_init_extra_kwargs() -> None:
    conn = HarlequinDatabricksAdapter(
        server_hostname=os.getenv("DATABRICKS_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        client_id=os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
    ).connect()
    assert conn
    conn.close()


def test_connect_raises_connection_error() -> None:
    with pytest.raises(HarlequinConnectionError):
        _ = HarlequinDatabricksAdapter(conn_str=("foo",)).connect()


@pytest.fixture
def connection() -> Iterator[HarlequinDatabricksConnection]:
    conn = HarlequinDatabricksAdapter(
        server_hostname=os.getenv("DATABRICKS_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        client_id=os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret=os.getenv("DATABRICKS_CLIENT_SECRET"),
        skip_legacy_indexing=True,
    ).connect()

    # yield conn is returned for each test fixture, then pytest runs conn.close() to clean up after
    # each test:
    yield conn
    conn.close()


def test_get_unity_catalog(connection: HarlequinDatabricksConnection) -> None:
    catalog = connection.get_catalog()
    assert isinstance(catalog, Catalog)
    assert catalog.items
    assert isinstance(catalog.items[0], CatalogItem)


def test_execute_select(connection: HarlequinDatabricksConnection) -> None:
    cur = connection.execute("select 1 as a")
    assert isinstance(cur, HarlequinCursor)
    assert cur.columns() == [("a", "##")]
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 1


def test_execute_select_dupe_cols(connection: HarlequinDatabricksConnection) -> None:
    cur = connection.execute("select 1 as a, 2 as a, 3 as a")
    assert isinstance(cur, HarlequinCursor)
    assert len(cur.columns()) == 3
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 3
    assert backend.row_count == 1


def test_set_limit(connection: HarlequinDatabricksConnection) -> None:
    cur = connection.execute("select 1 as a union all select 2 union all select 3")
    assert isinstance(cur, HarlequinCursor)
    cur = cur.set_limit(2)
    assert isinstance(cur, HarlequinCursor)
    data = cur.fetchall()
    backend = create_backend(data)
    assert backend.column_count == 1
    assert backend.row_count == 2


def test_execute_raises_query_error(connection: HarlequinDatabricksConnection) -> None:
    with pytest.raises(HarlequinQueryError):
        _ = connection.execute("selec;")


def test_close(connection: HarlequinDatabricksConnection) -> None:
    connection.close()
    with pytest.raises(databricks_sql.exc.Error):
        connection.conn.cursor()  # cannot open a Cursor from a closed Databricks connection
