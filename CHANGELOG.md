# harlequin-databricks CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.0] - 2024-02-09

### Features

-   Faster indexing for Unity Catalog assets. Makes loading & refreshing Harlequin's Data Catalog
pane much quicker for Databricks instances running Unity Catalog. The new method fetches metadata
for Unity Catalog assets from `system.information_schema`, requiring only two SQL queries to do so.
This is much faster than the old method, which required separate SQL calls for each table. The old
method is still in use for indexing legacy metastores (e.g. `hive_metastore`) however, as that
metadata is not contained in Information schema:
https://docs.databricks.com/en/sql/language-manual/sql-ref-information-schema.html
-   Add new command line flag `--skip-legacy-indexing` to skip the indexing of legacy metastores.
Setting this flag is recommended if your Databricks instance runs Unity Catalog and you do not want
the overhead of slow indexing of legacy metastores. When this flag is set, only Unity Catalog
assets will show up in the Data Catalog pane.

## [0.1.1] - 2024-02-08

### Bug Fixes

-   Ensure catalogs, schemas & tables are sorted alphabetically in Data Catalog pane.
-   Ensure order of columns shown in Data Catalog pane is correct for each table.

## [0.1.0] - 2024-02-04

### Features

-   Adds a Databricks adapter for SQL warehouses and DBR interactive clusters.

[Unreleased]: https://github.com/alexmalins/harlequin-databricks/compare/0.2.0...HEAD

[0.2.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.1.1...0.2.0

[0.1.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.1.0...0.1.1

[0.1.0]: https://github.com/alexmalins/harlequin-databricks/compare/a7156a0f90418d2130838b737592528c89a43ac8...0.1.0
