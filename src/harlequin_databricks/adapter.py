from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
)

import pyarrow.compute as pc
from databricks import sql as databricks_sql
from harlequin import (
    HarlequinAdapter,
    HarlequinConnection,
    HarlequinCursor,
)
from harlequin.catalog import (
    Catalog,
    CatalogItem,
)
from harlequin.exception import (
    HarlequinConfigError,
    HarlequinConnectionError,
    HarlequinQueryError,
)

from harlequin_databricks.cli_options import DATABRICKS_ADAPTER_OPTIONS
from harlequin_databricks.completions import load_completions

if TYPE_CHECKING:
    from databricks.sql.client import Cursor as DatabricksCursor
    from harlequin.autocomplete.completion import HarlequinCompletion
    from textual_fastdatatable.backend import AutoBackendType


def _fetch(
    cursor: DatabricksCursor, limit: int | None = None
) -> AutoBackendType | None:
    try:
        rows = cursor.fetchmany_arrow(limit) if limit else cursor.fetchall_arrow()
    except databricks_sql.DatabaseError as e:
        if (
            e.message.startswith("Invalid OperationHandle:")
            and e.__class__.__name__ == "DatabaseError"
        ):  # maybe user pressed `Cancel Query` button here
            return None
        raise HarlequinQueryError(
            msg=repr(e),
            title="Harlequin encountered an error while querying Databricks.",
        ) from e
    return rows


class HarlequinDatabricksCursor(HarlequinCursor):
    def __init__(self, cursor: DatabricksCursor, *args: Any, **kwargs: Any) -> None:
        self.cur = cursor
        self._limit: int | None = None

    def columns(self) -> list[tuple[str, str]]:
        assert self.cur.description is not None
        return [
            (col_metadata[0], self._get_short_col_type(col_metadata[1].upper()))
            for col_metadata in self.cur.description
        ]

    def set_limit(self, limit: int) -> HarlequinDatabricksCursor:
        self._limit = limit
        return self

    def fetchall(self) -> AutoBackendType | None:
        return _fetch(self.cur, self._limit)

    @staticmethod
    def _get_short_col_type(info_schema_type: str) -> str:
        mapping = {
            "ARRAY": "[]",
            "BIGINT": "###",
            "BINARY": "010",
            "BOOLEAN": "t/f",
            "DATE": "d",
            "DECIMAL": "#.#",
            "DOUBLE": "#.#",
            "FLOAT": "#.#",
            "INT": "##",
            # 2024/01/28 Alex Malins: Not currently used as databricks-sql-python returns intervals
            # as `string` data type for some reason:
            # https://github.com/databricks/databricks-sql-python/issues/336
            "INTERVAL": "|-|",
            "LONG": "###",
            "MAP": "m",
            "NULL": "nul",
            "SHORT": "#",
            "SMALLINT": "#",
            "STRING": "s",
            "STRUCT": "{}",
            "TIMESTAMP": "ts",
            # 2024/01/28 Alex Malins: `TIMESTAMP_NTZ` type not tested as this type is not enabled
            # on databricks instance I have access to (`TIMESTAMP` is always returned).
            "TIMESTAMP_NTZ": "ntz",
            "TINYINT": "#",
            # 2024/01/28 Alex Malins: Not currently used as databricks-sql-python returns voids as
            # `string` data type for some reason:
            # https://github.com/databricks/databricks-sql-python/issues/336
            "VOID": "nul",
        }
        return mapping.get(info_schema_type, "?")


class HarlequinDatabricksConnection(HarlequinConnection):
    def __init__(
        self,
        *_: Any,
        init_message: str = "",
        options: dict[str, Any],
    ) -> None:
        self._original_init_message = init_message
        self.skip_legacy_indexing = options.pop("skip_legacy_indexing")
        self.init_path = options.pop("init_path")
        self.no_init = options.pop("no_init")

        self.init_script = (
            self._read_init_script(self.init_path)
            if self.init_path is not None and not self.no_init
            else None
        )

        # store the state of the catalog to reuse if the user pressing `Cancel Query` stops the
        # catalog indexing thread in-flight:
        self._existing_catalog: Catalog = Catalog(items=[])

        # Set up OAuth machine-to-machine (M2M) authentication:
        client_id = options.pop("client_id")
        client_secret = options.pop("client_secret")
        if client_id or client_secret:
            if client_id is None or client_secret is None:
                raise HarlequinConnectionError(
                    msg=(
                        "To use OAuth M2M you must supply both --client-id and "
                        "--client-secret CLI arguments."
                    ),
                    title="Harlequin could not connect to Databricks SQL warehouse.",
                )

            try:
                from databricks.sdk.core import (
                    Config,
                    oauth_service_principal,
                )

                if TYPE_CHECKING:
                    from databricks.sdk.credentials_provider import (
                        CredentialsProvider,
                    )

                def credentials_provider() -> CredentialsProvider | None:
                    config = Config(
                        host=f"https://{options['server_hostname']}",
                        client_id=client_id,
                        client_secret=client_secret,
                    )
                    return oauth_service_principal(config)  # type:ignore

                options["credentials_provider"] = credentials_provider
            except ImportError as e:
                raise HarlequinConnectionError(
                    msg="To use OAuth M2M you must install `databricks-sdk` as an extra",
                    title="Harlequin could not connect to Databricks SQL warehouse.",
                ) from e

        self._connection_options = options
        self._connect_and_run_init_script()

    def _connect_and_run_init_script(self) -> None:
        try:
            self.conn = databricks_sql.connect(**self._connection_options)
        except Exception as e:
            raise HarlequinConnectionError(
                msg=repr(e),
                title="Harlequin could not connect to Databricks SQL warehouse.",
            ) from e

        msg = ""
        if self.init_script:
            try:
                count = 0
                for cmd in self.init_script.split(";"):
                    stripped_cmd = cmd.strip()
                    if not stripped_cmd:
                        continue
                    self.execute(stripped_cmd)
                    count += 1
            except HarlequinQueryError as e:
                msg = f"Attempted to execute script at {self.init_path}\n{e}"
                raise HarlequinConnectionError(
                    msg,
                    title="Databricks errored while executing your initialization script.",
                ) from e
            else:
                if count > 0:
                    msg = (
                        f"Executed {count} {'command' if count == 1 else 'commands'} "
                        f"from {self.init_path}"
                    )

        self.init_message = self._original_init_message + ("\n" + msg if msg else "")

    @staticmethod
    def _read_init_script(init_path: Path) -> str:
        try:
            with init_path.expanduser().open("r") as f:
                init_script = f.read()
        except OSError:
            init_script = ""
        return init_script

    def execute(self, query: str) -> HarlequinDatabricksCursor | None:
        try:
            cur = self.conn.cursor()
            cur.execute(query)
        except databricks_sql.DatabaseError as e:
            if (
                e.message.startswith("Invalid OperationHandle:")
                and e.__class__.__name__ == "DatabaseError"
            ):  # maybe user pressed `Cancel Query` button here
                return None
            raise HarlequinQueryError(
                msg=repr(e),
                title="Harlequin encountered an error while querying Databricks.",
            ) from e
        return HarlequinDatabricksCursor(cur)

    def cancel(self) -> None:
        # This is a hacky way to cancel all ongoing queries of a Databricks Connection. It kills
        # and reestablishes a fresh connection, as closing a Databricks Connection will cancel all
        # in-flight queries which that connection started. This is a hack around the Databricks
        # Python SQL Connector not offering a Connection-level `interrupt()` or `cancel()` method
        # to cancel all in-flight queries, without having to kill and reestablish a new connection.
        # The Databricks Python SQL Connector does offer a `cancel()` method at the Cursor-level,
        # but this is hard to implement within Harlequin's existing adapter framework which
        # requires cancellation of all ongoing queries of the Connection.

        old_conn = self.conn
        self._connect_and_run_init_script()
        old_conn.close()

    def get_catalog(self) -> Catalog:
        """Query Databricks asserts and store in a Harlequin Catalog (for the Data Catalog pane).

        If the user presses the `Cancel Query` button while this function is executing
        asynchronously, this function will return the Catalog as it stood before this function was
        called (from the `self._existing_catalog` instance variable).
        """

        catalog_items: list[CatalogItem] = []
        unity_catalog_result = self._get_unity_catalogs(catalog_items)

        # maybe user pressed `Cancel Query` button interrupting the indexing of Unity Catalog
        # assets:
        if unity_catalog_result is None:
            return self._existing_catalog
        catalog_items, seen_catalogs = unity_catalog_result

        if self.skip_legacy_indexing:
            return Catalog(items=catalog_items)

        # Index legacy metastore metadata (e.g. `hive_metastore`):
        with self.conn.cursor() as cursor:
            cursor.catalogs()
            catalogs = _fetch(cursor)
            if catalogs is None:  # maybe user pressed `Cancel Query` button
                return self._existing_catalog
            catalogs = catalogs.sort_by([("TABLE_CAT", "ascending")])

            for catalog_arrow in catalogs["TABLE_CAT"]:
                catalog = catalog_arrow.as_py()
                if catalog in seen_catalogs:
                    continue
                seen_catalogs.append(catalog)

                cursor.schemas(catalog_name=catalog)
                schemas = _fetch(cursor)
                if schemas is None:  # maybe user pressed `Cancel Query` button
                    return self._existing_catalog
                schemas = schemas.sort_by([("TABLE_SCHEM", "ascending")])
                schema_items: list[CatalogItem] = []

                for schema_arrow in schemas["TABLE_SCHEM"]:
                    schema = schema_arrow.as_py()

                    cursor.tables(catalog_name=catalog, schema_name=schema)
                    tables = _fetch(cursor)
                    if tables is None:  # maybe user pressed `Cancel Query` button
                        return self._existing_catalog
                    tables = tables.sort_by([("TABLE_NAME", "ascending")])
                    table_items: list[CatalogItem] = []

                    for table_arrow, table_type_arrow in zip(
                        tables["TABLE_NAME"],
                        tables["TABLE_TYPE"],
                    ):
                        table = table_arrow.as_py()

                        cursor.columns(
                            catalog_name=catalog, schema_name=schema, table_name=table
                        )
                        columns = _fetch(cursor)
                        if columns is None:  # maybe user pressed `Cancel Query` button
                            return self._existing_catalog
                        columns = columns.sort_by([("ORDINAL_POSITION", "ascending")])

                        column_items = [
                            CatalogItem(
                                qualified_identifier=(
                                    f"{catalog}.{schema}.{table}.{column.as_py()}"
                                ),
                                query_name=column.as_py(),
                                label=column.as_py(),
                                type_label=column_type.as_py(),
                            )
                            for column, column_type in zip(
                                columns["COLUMN_NAME"], columns["TYPE_NAME"]
                            )
                        ]

                        table_items.append(
                            CatalogItem(
                                qualified_identifier=f"{catalog}.{schema}.{table}",
                                query_name=f"{catalog}.{schema}.{table}",
                                label=table,
                                type_label=table_type_arrow.as_py(),
                                children=column_items,
                            )
                        )
                    schema_items.append(
                        CatalogItem(
                            qualified_identifier=f"{catalog}.{schema}",
                            query_name=f"{catalog}.{schema}",
                            label=schema,
                            type_label="s",
                            children=table_items,
                        )
                    )
                catalog_items.append(
                    CatalogItem(
                        qualified_identifier=catalog,
                        query_name=catalog,
                        label=catalog,
                        type_label="catalog",
                        children=schema_items,
                    )
                )
            # Sort the catalogs again to ensure legacy and unity catalogs appear alphabetically:
            catalog_items = [
                catalog_item
                for _, catalog_item in sorted(zip(seen_catalogs, catalog_items))
            ]

            self._existing_catalog = Catalog(items=catalog_items)
            return self._existing_catalog

    def _get_unity_catalogs(
        self,
        catalog_items: list[CatalogItem],
    ) -> tuple[list[CatalogItem], list[str]] | None:
        """Index Unity Catalog assets.

        This method returns a list of Harlequin CatalogItems containing the Unity Catalog assets
        (only) in the Databricks instance, and a list of the names of the Unity catalogs.

        This method does not return metadata for any legacy Hive metastore assets, as that data
        does not exist in `system.information_schema`:
        https://docs.databricks.com/en/sql/language-manual/sql-ref-information-schema.html

        Only two SQL queries are required to fetch all metadata on Unity Catalog assets from the
        information schema.

        If one of the SQL queries to fetch the Unity Catalog metadata fails because the user
        presses the `Cancel Query` button, this function will return None, triggering
        `get_catalog()` to return the Catalog as it stood before the call to `get_catalog()`.
        """

        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    """SELECT
                    table_catalog
                    , table_schema
                    , table_name
                    , table_type
                    FROM system.information_schema.tables"""
                )
            except databricks_sql.DatabaseError as e:
                if (
                    e.message.startswith("Invalid OperationHandle:")
                    and e.__class__.__name__ == "DatabaseError"
                ):  # maybe user pressed `Cancel Query` button here
                    return None
                raise HarlequinQueryError(
                    msg=repr(e),
                    title=(
                        "Harlequin encountered an error while querying Databricks to index the "
                        "Unity Catalog assets."
                    ),
                ) from e
            all_tables = _fetch(cursor)
            if all_tables is None:  # maybe user pressed `Cancel Query` button here
                return None
            all_tables = all_tables.sort_by(
                [
                    ("table_catalog", "ascending"),
                    ("table_schema", "ascending"),
                    ("table_name", "ascending"),
                ]
            )

            try:
                cursor.execute(
                    """SELECT
                    table_catalog
                    , table_schema
                    , table_name
                    , column_name
                    , ordinal_position
                    , data_type
                    FROM system.information_schema.columns"""
                )
            except databricks_sql.DatabaseError as e:
                if (
                    e.message.startswith("Invalid OperationHandle:")
                    and e.__class__.__name__ == "DatabaseError"
                ):  # maybe user pressed `Cancel Query` button here
                    return None
                raise HarlequinQueryError(
                    msg=repr(e),
                    title=(
                        "Harlequin encountered an error while querying Databricks to index the "
                        "Unity Catalog assets."
                    ),
                ) from e
            all_cols = _fetch(cursor)
            if all_cols is None:  # maybe user pressed `Cancel Query` button here
                return None
            all_cols = all_cols.sort_by(
                [
                    ("table_catalog", "ascending"),
                    ("table_schema", "ascending"),
                    ("table_name", "ascending"),
                    ("ordinal_position", "ascending"),
                ]
            )
            unity_catalogs = all_tables["table_catalog"].unique()

            for catalog_arrow in unity_catalogs:
                catalog = catalog_arrow.as_py()

                schemas = all_tables.filter(pc.field("table_catalog") == catalog_arrow)
                schema_items: list[CatalogItem] = []

                for schema_arrow in schemas["table_schema"].unique():
                    schema = schema_arrow.as_py()

                    tables = schemas.filter(pc.field("table_schema") == schema_arrow)
                    table_items: list[CatalogItem] = []

                    for table_arrow, table_type_arrow in zip(
                        tables["table_name"],
                        tables["table_type"],
                    ):
                        table = table_arrow.as_py()

                        columns = all_cols.filter(
                            (pc.field("table_catalog") == catalog_arrow)
                            & (pc.field("table_schema") == schema_arrow)
                            & (pc.field("table_name") == table_arrow)
                        )
                        column_items = [
                            CatalogItem(
                                qualified_identifier=(
                                    f"{catalog}.{schema}.{table}.{column.as_py()}"
                                ),
                                query_name=column.as_py(),
                                label=column.as_py(),
                                type_label=column_type.as_py(),
                            )
                            for column, column_type in zip(
                                columns["column_name"], columns["data_type"]
                            )
                        ]

                        table_items.append(
                            CatalogItem(
                                qualified_identifier=f"{catalog}.{schema}.{table}",
                                query_name=f"{catalog}.{schema}.{table}",
                                label=table,
                                type_label=table_type_arrow.as_py(),
                                children=column_items,
                            )
                        )
                    schema_items.append(
                        CatalogItem(
                            qualified_identifier=f"{catalog}.{schema}",
                            query_name=f"{catalog}.{schema}",
                            label=schema,
                            type_label="s",
                            children=table_items,
                        )
                    )
                catalog_items.append(
                    CatalogItem(
                        qualified_identifier=catalog,
                        query_name=catalog,
                        label=catalog,
                        type_label="catalog",
                        children=schema_items,
                    )
                )
            return catalog_items, unity_catalogs.to_pylist()

    def get_completions(self) -> list[HarlequinCompletion]:
        return load_completions()

    def close(self) -> None:
        if self.conn:
            self.conn.close()


class HarlequinDatabricksAdapter(HarlequinAdapter):
    ADAPTER_OPTIONS = DATABRICKS_ADAPTER_OPTIONS
    IMPLEMENTS_CANCEL = True

    def __init__(
        self,
        server_hostname: str | None = None,
        http_path: str | None = None,
        access_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth_type: str | None = None,
        skip_legacy_indexing: bool | None = False,
        client_id: str | None = None,
        client_secret: str | None = None,
        init_path: Path | str | None = None,
        no_init: bool | str = False,
        **_: Any,
    ) -> None:
        try:
            init_path = (
                Path(init_path).expanduser().resolve()
                if init_path is not None
                else Path.home() / ".databricksrc"
            )
            no_init = bool(no_init)
        except (ValueError, TypeError) as e:
            raise HarlequinConfigError(
                msg=f"Databricks adapter received bad config value: {e}",
                title="Harlequin could not initialize the selected adapter.",
            ) from e

        self.options = {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "access_token": access_token,
            "username": username,
            "password": password,
            "auth_type": auth_type,
            "skip_legacy_indexing": skip_legacy_indexing,
            "client_id": client_id,
            "client_secret": client_secret,
            "init_path": init_path,
            "no_init": no_init,
        }

    def connect(self) -> HarlequinDatabricksConnection:
        return HarlequinDatabricksConnection(options=self.options)
