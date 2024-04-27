from __future__ import annotations

from typing import Any

import pyarrow.compute as pc  # type:ignore
from databricks import sql as databricks_sql  # type:ignore
from databricks.sql.client import Cursor as DatabricksCursor  # type:ignore
from harlequin import (
    HarlequinAdapter,
    HarlequinConnection,
    HarlequinCursor,
)
from harlequin.autocomplete.completion import HarlequinCompletion
from harlequin.catalog import Catalog, CatalogItem
from harlequin.exception import HarlequinConnectionError, HarlequinQueryError
from textual_fastdatatable.backend import AutoBackendType

from harlequin_databricks.cli_options import DATABRICKS_ADAPTER_OPTIONS
from harlequin_databricks.completions import load_completions


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

    def fetchall(self) -> AutoBackendType:
        try:
            if self._limit is None:
                return self.cur.fetchall_arrow()
            return self.cur.fetchmany_arrow(self._limit)
        except Exception as e:
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e

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
        self.init_message = init_message
        self.skip_legacy_indexing = options.pop("skip_legacy_indexing")
        try:
            self.conn = databricks_sql.connect(**options)
        except Exception as e:
            raise HarlequinConnectionError(
                msg=str(e),
                title="Harlequin could not connect to Databricks SQL warehouse.",
            ) from e

    def execute(self, query: str) -> HarlequinDatabricksCursor:
        try:
            cur = self.conn.cursor()
            cur.execute(query)
        except Exception as e:
            cur.close()
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e
        return HarlequinDatabricksCursor(cur)

    def get_catalog(self) -> Catalog:
        catalog_items: list[CatalogItem] = []
        catalog_items, seen_catalogs = self._get_unity_catalogs(catalog_items)

        if self.skip_legacy_indexing:
            return Catalog(items=catalog_items)

        # Index legacy metastore metadata (e.g. `hive_metastore`):
        with self.conn.cursor() as cursor:
            cursor.catalogs()
            catalogs = cursor.fetchall_arrow()
            catalogs = catalogs.sort_by([("TABLE_CAT", "ascending")])

            for catalog_arrow in catalogs["TABLE_CAT"]:
                catalog = catalog_arrow.as_py()
                if catalog in seen_catalogs:
                    continue
                seen_catalogs.append(catalog)

                cursor.schemas(catalog_name=catalog)
                schemas = cursor.fetchall_arrow()
                schemas = schemas.sort_by([("TABLE_SCHEM", "ascending")])
                schema_items: list[CatalogItem] = []

                for schema_arrow in schemas["TABLE_SCHEM"]:
                    schema = schema_arrow.as_py()

                    cursor.tables(catalog_name=catalog, schema_name=schema)
                    tables = cursor.fetchall_arrow()
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
                        columns = cursor.fetchall_arrow()
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
            return Catalog(items=catalog_items)

    def _get_unity_catalogs(
        self,
        catalog_items: list[CatalogItem],
    ) -> tuple[list[CatalogItem], list[str]]:
        """It is possible to index quickly assets on Databricks instances running Unity Catalog, as
        only two SQL queries are required to fetch all Unity Catalog assets.

        This method returns a list of Harlequin CatalogItems containing the Unity Catalog assets
        (only) in the Databricks instance, and a list of the names of the Unity catalogs.

        This method does not return metadata for any legacy Hive metastore assets, as that data
        does not exist in `system.information_schema`:
        https://docs.databricks.com/en/sql/language-manual/sql-ref-information-schema.html
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
            except databricks_sql.ServerOperationError as e:
                if e.message.startswith("[TABLE_OR_VIEW_NOT_FOUND]"):
                    return catalog_items, []
                raise HarlequinQueryError(
                    msg=str(e),
                    title="Harlequin encountered an error while executing your query.",
                ) from e
            all_tables = cursor.fetchall_arrow()
            all_tables = all_tables.sort_by(
                [
                    ("table_catalog", "ascending"),
                    ("table_schema", "ascending"),
                    ("table_name", "ascending"),
                ]
            )

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
            all_cols = cursor.fetchall_arrow()
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

    def __init__(
        self,
        server_hostname: str | None = None,
        http_path: str | None = None,
        access_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        auth_type: str | None = None,
        skip_legacy_indexing: bool | None = False,
        **_: Any,
    ) -> None:
        self.options = {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "access_token": access_token,
            "username": username,
            "password": password,
            "auth_type": auth_type,
            "skip_legacy_indexing": skip_legacy_indexing,
        }

    def connect(self) -> HarlequinDatabricksConnection:
        conn = HarlequinDatabricksConnection(options=self.options)
        return conn
