from __future__ import annotations

from typing import Any, Sequence

from databricks import sql as databricks_sql
from databricks.sql.client import Cursor as DatabricksCursor
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
            "MAP": "m",
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
            cur.execute(query)  # type: ignore
        except Exception as e:
            cur.close()
            raise HarlequinQueryError(
                msg=str(e),
                title="Harlequin encountered an error while executing your query.",
            ) from e
        return HarlequinDatabricksCursor(cur)

    def get_catalog(self) -> Catalog:
        with self.conn.cursor() as cursor:
            cursor.catalogs()
            catalogs = cursor.fetchall_arrow()
            catalogs = catalogs.sort_by([("TABLE_CAT", "ascending")])
            catalog_items: list[CatalogItem] = []

            for catalog_arrow in catalogs["TABLE_CAT"]:
                catalog = catalog_arrow.as_py()

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
                                    f'"{catalog}"."{schema}"."{table}"."{column.as_py()}"'
                                ),
                                query_name=f'"{column.as_py()}"',
                                label=column.as_py(),
                                type_label=column_type.as_py(),
                            )
                            for column, column_type in zip(
                                columns["COLUMN_NAME"], columns["TYPE_NAME"]
                            )
                        ]

                        table_items.append(
                            CatalogItem(
                                qualified_identifier=f'"{catalog}"."{schema}"."{table}"',
                                query_name=f'"{catalog}"."{schema}"."{table}"',
                                label=table,
                                type_label=table_type_arrow.as_py(),
                                children=column_items,
                            )
                        )
                    schema_items.append(
                        CatalogItem(
                            qualified_identifier=f'"{catalog}"."{schema}"',
                            query_name=f'"{catalog}"."{schema}"',
                            label=schema,
                            type_label="s",
                            children=table_items,
                        )
                    )
                catalog_items.append(
                    CatalogItem(
                        qualified_identifier=f'"{catalog}"',
                        query_name=f'"{catalog}"',
                        label=catalog,
                        type_label="catalog",
                        children=schema_items,
                    )
                )
            return Catalog(items=catalog_items)

    def get_completions(self) -> list[HarlequinCompletion]:
        return load_completions()


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
        **_: Any,
    ) -> None:
        self.options = {
            "server_hostname": server_hostname,
            "http_path": http_path,
            "access_token": access_token,
            "username": username,
            "password": password,
            "auth_type": auth_type,
        }

    def connect(self) -> HarlequinDatabricksConnection:
        conn = HarlequinDatabricksConnection(options=self.options)
        return conn
