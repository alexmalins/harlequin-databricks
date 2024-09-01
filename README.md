# harlequin-databricks

[![PyPI](https://img.shields.io/pypi/v/harlequin-databricks)](https://pypi.org/project/harlequin-databricks/)
[![Conda](https://anaconda.org/conda-forge/harlequin-databricks/badges/version.svg)](https://anaconda.org/conda-forge/harlequin-databricks)
[![Python Version](https://img.shields.io/pypi/pyversions/harlequin-databricks)](https://pypi.org/project/harlequin-databricks/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/alexmalins/harlequin-databricks/actions/workflows/code_quality.yml)
[![License: MIT](https://img.shields.io/pypi/l/harlequin-databricks)](https://github.com/alexmalins/harlequin-databricks/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/harlequin-databricks)](https://pepy.tech/project/harlequin-databricks)

A [Harlequin](https://harlequin.sh) adapter for Databricks. Supports connecting to Databricks SQL
warehouses or Databricks Runtime (DBR) interactive clusters.

<img src="img/harlequin_databricks.jpg" alt="harlequin-databricks" width="945">

## Installation

`harlequin-databricks` depends on `harlequin`, so installing this package will also install Harlequin.

### Using pip

To install this adapter into an activated virtual environment:

```bash
pip install harlequin-databricks
```

### Using poetry

```bash
poetry add harlequin-databricks
```

### Using pipx

If you do not already have Harlequin installed:

```bash
pipx install harlequin-databricks
```

If you would like to add the Databricks adapter to an existing Harlequin installation:

```bash
pipx inject harlequin harlequin-databricks
```

### As an Extra

Alternatively, you can install Harlequin with the `databricks` extra:

```bash
pip install harlequin[databricks]
```

```bash
poetry add harlequin[databricks]
```

```bash
pipx install harlequin[databricks]
```

## Usage and Configuration

For a minimum connection you are going to need:

- server-hostname
- http-path
- access-token

```bash
harlequin -a databricks --server-hostname my_databricks.cloud.databricks.com --http-path /sql/1.0/endpoints/1234567890abcdef --access-token dabpi***
```

Authentication is also possible using a username and password (known as basic authentication):

```bash
harlequin -a databricks --server-hostname my_databricks.cloud.databricks.com --http-path /sql/1.0/endpoints/1234567890abcdef --username my_user --password my_pass
```

Or by using [OAuth user-to-machine (U2M) authentication](https://docs.databricks.com/en/dev-tools/python-sql-connector.html#auth-u2m)
- supply `databricks-oauth` or `azure-oauth` to the `--auth-type` CLI argument:

```bash
harlequin -a databricks --server-hostname my_databricks.cloud.databricks.com --http-path /sql/1.0/endpoints/1234567890abcdef --auth-type databricks-oauth
```

Or via [OAuth machine-to-machine (M2M) authentication](https://docs.databricks.com/en/dev-tools/python-sql-connector.html#oauth-machine-to-machine-m2m-authentication),
which also requires you `pip install databricks-sdk` as an additional dependency
([databricks-sdk](https://github.com/databricks/databricks-sdk-py) is an optional dependency of
`harlequin-databricks`):

```bash
harlequin -a databricks --server-hostname my_databricks.cloud.databricks.com --http-path /sql/1.0/endpoints/1234567890abcdef --client-id *** --client-secret ***
```

For more details on command line options, run:

```bash
harlequin --help
```

For more information, see the
[harlequin-databricks Docs](https://harlequin.sh/docs/databricks/index).

## Using Unity Catalog and want fast Data Catalog indexing?

Supply the `--skip-legacy-indexing` command line flag if you do not care about legacy metastores
(e.g. `hive_metastore`) being indexed in Harlequin's Data Catalog pane.

This flag will skip indexing of old non-Unity Catalog metastores (i.e. they won't appear in the
Data Catalog pane with this flag).

Because of the way legacy Databricks metastores works, a separate SQL query is required to fetch
the metadata of each table in a legacy metastore. This means indexing them for Harlequin's Data Catalog pane is slow.

Databricks's Unity Catalog upgrade brought
[Information Schema](https://docs.databricks.com/en/sql/language-manual/sql-ref-information-schema.html),
which allows harlequin-databricks to fetch metadata for all Unity Catalog assets with only two SQL queries.

So if your Databricks instance is running Unity Catalog, and you no longer care about the legacy
metastores, setting the `--skip-legacy-indexing` CLI flag is recommended as it will mean
much faster indexing & refreshing of the assets in the Data Catalog pane.

## Issues, Contributions and Feature Requests

Please report bugs/issues with this adapter via the GitHub
[issues](https://github.com/alexmalins/harlequin-databricks/issues) page. You are welcome to
attempt fixes yourself by forking this repo then opening an [PR](https://github.com/alexmalins/harlequin-databricks/pulls).

For feature suggestions, please post in the
[discussions](https://github.com/alexmalins/harlequin-databricks/discussions).

## Special thanks to...

[Ted Conbeer](https://github.com/tconbeer), [Josh Temple](https://github.com/joshtemple) &
[Tyler Hillery](https://github.com/TylerHillery).
