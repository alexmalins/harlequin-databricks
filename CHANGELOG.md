# harlequin-databricks CHANGELOG

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.6.4] - 2025-12-19

### Bug Fixes

- Add explicit Python 3.14 support (#23 & #25).

## [0.6.3] - 2025-12-14

### Bug Fixes

- Drop Python 3.9 support (#24).
- Update Databricks SQL functions list for Harlequin syntax highlighting and autocomplete (#24).

## [0.6.2] - 2025-07-10

### Bug Fixes

- Ensure LICENSE file gets packaged in distribution - this is needed for the conda-forge feedstock
(cf. https://github.com/conda-forge/harlequin-databricks-feedstock/pull/13) (#22).

## [0.6.1] - 2025-07-06

### Features

- Relax `harlequin` version to `>=2.0.4` to allow conda-forge builds again (#21).

### Code Quality

- Add classifiers and keywords to `pyproject.toml` (#20).
- Update URLs for Databricks SQL keywords (#20).

## [0.6.0] - 2025-07-05

### Breaking Changes

- Require `databricks-sql-connector>=4.0.4` to fix unable to index data catalog bug (#18 & #19).
- Require `harlequin>=2.1.2` (#19).

### Features

- Recommend [uv](https://github.com/astral-sh/uv) as installation method (#19).
- Update functions & keywords syntax highlighting lists (#19).

### Code Quality

- Use [uv](https://github.com/astral-sh/uv) for package management, build backend and CI (#19).
- Use [ruff](https://github.com/astral-sh/ruff) for linting and code formatting (#19).
- Drop functional tests in CI against Databricks as test Databricks instance no longer works (#19).

## [0.5.2] - 2025-01-07

### Breaking Changes

- Drops support for Python 3.8 (#17).
- Require latest versions of Harlequin `>=1.25.2`, databricks-sql-connector `>=3.7.0` and
databricks-sdk `>=0.40.0` (optional extra), and avoid upper version bounds on requirements to avoid
dependency hell (more here: https://github.com/databricks/databricks-sql-python/pull/452 &
https://github.com/tconbeer/harlequin/pull/714/commits/a50dfacd17e6626002c21e3c3bfd7e80203a0ea8#diff-50c86b7ed8ac2cf95bd48334961bf0530cdc77b5a56f852c5c61b89d735fd711R64)
(#17).

### Code Quality

- Reduce unused mypy ignores (#17).

## [0.5.1] - 2024-09-21

### Bug Fixes

-   Fix bug to properly resolve initialization script paths starting with `~` (i.e. user's home
dir) supplied to `--init-path`.

## [0.5.0] - 2024-09-21

### Features

-   Add support for initialization scripts. By default harlequin-databricks will attempt to run an
initialization script of SQL commands against Databricks from `~/.databricksrc` or from the file
specified via the `--init-path` CLI option. This means you can e.g. set a default catalog
(`USE CATALOG ...`), timezone, or set of user-defined variables for the session. It is possible to
disable initialization via the `--no-init` CLI flag, having no  `~/.databricksrc` file, or feeding
a non-existent file path to `--init-path`. (#14)

## [0.4.0] - 2024-09-01

### Features

-   Add support for cancelling queries mid-flight. Requires Harlequin `>=1.24.0` which introduced
the "Cancel Query" button.
-   Add support for Azure in OAuth user-to-machine authentication for Databricks running on Azure.
-   Add support for OAuth machine-to-machine (M2M) authentication to Databricks. This allows you to
use service principle credentials to connect to Databricks via Harlequin, useful for testing. To
use OAuth M2M, supply a `--client-id` and a `--client-secret` (i.e. a service principle OAuth
token) via CLI arguments.
-   Better error handling and debug messages when database query errors occur.

## [0.3.1] - 2024-08-04

-   Fix `UnicodeDecodeError` on Windows due to incorrectly attempting to read `functions.csv` using
CP-1252. Now UTF-8 is enforced on all file writes and reads (#7).
-   Update list of Databricks SQL functions for completions (valid as of August 2, 2024).
-   Add harlequin-databricks screenshot to README.

## [0.3.0] - 2024-04-27

-   Implement the `close()` method of `HarlequinConnection` so that the Databricks connection is
closed when Harlequin exits.
-   Update list of Databricks SQL functions for completions (valid as of April 24, 2024).

## [0.2.1] - 2024-02-15

### Bug Fixes

-   Fix SQL created in the Query Editor by double clicking on catalog, schema, table or column
names in the Data Catalog pane. Previously items were wrapped in double quotes, which is invalid
Databricks SparkSQL.
-   Fix outstanding ruff and mypy errors.

## [0.2.0] - 2024-02-10

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

### Bug Fixes

-   Fix minor formatting (black), types (mypy) & linting (ruff) issues, and a test failure.
-   Don't use underscores in CLI option names, i.e. make it so the only acceptable option version
is the one written with hyphens not underscores.

## [0.1.1] - 2024-02-08

### Bug Fixes

-   Ensure catalogs, schemas & tables are sorted alphabetically in Data Catalog pane.
-   Ensure order of columns shown in Data Catalog pane is correct for each table.

## [0.1.0] - 2024-02-04

### Features

-   Adds a Databricks adapter for SQL warehouses and DBR interactive clusters.

[Unreleased]: https://github.com/alexmalins/harlequin-databricks/compare/0.6.4...HEAD

[0.6.4]: https://github.com/alexmalins/harlequin-databricks/compare/0.6.3...0.6.4

[0.6.3]: https://github.com/alexmalins/harlequin-databricks/compare/0.6.2...0.6.3

[0.6.2]: https://github.com/alexmalins/harlequin-databricks/compare/0.6.1...0.6.2

[0.6.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.6.0...0.6.1

[0.6.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.5.2...0.6.0

[0.5.2]: https://github.com/alexmalins/harlequin-databricks/compare/0.5.1...0.5.2

[0.5.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.5.0...0.5.1

[0.5.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.4.0...0.5.0

[0.4.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.3.1...0.4.0

[0.3.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.3.0...0.3.1

[0.3.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.2.1...0.3.0

[0.2.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.2.0...0.2.1

[0.2.0]: https://github.com/alexmalins/harlequin-databricks/compare/0.1.1...0.2.0

[0.1.1]: https://github.com/alexmalins/harlequin-databricks/compare/0.1.0...0.1.1

[0.1.0]: https://github.com/alexmalins/harlequin-databricks/compare/a7156a0f90418d2130838b737592528c89a43ac8...0.1.0
