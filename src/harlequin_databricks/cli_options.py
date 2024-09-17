from pathlib import Path

from harlequin.options import FlagOption, PathOption, SelectOption, TextOption

server_hostname = TextOption(
    name="server-hostname",
    description="Databricks instance server hostname (ex. ****.cloud.databricks.com)",
)

http_path = TextOption(
    name="http-path",
    description=(
        "HTTP path of either a Databricks SQL warehouse (ex. /sql/1.0/endpoints/1234567890abcdef)"
        "or a Databricks runtime interactive cluster (ex. "
        "/sql/protocolv1/o/1234567890123456/1234-123456-slid123)"
    ),
    # 2024/01/28 Alex Malins: disabling these short_decls due to conflict with other adapters
    # (https://github.com/tconbeer/harlequin/issues/432ß):
    # `"short_decls=[-p", "--path"]`
)

access_token = TextOption(
    name="access-token",
    description="Your Databricks personal access token (if using PAT authentication)",
    # 2024/01/28 Alex Malins: disabling these short_decls due to conflict with other adapters
    # (https://github.com/tconbeer/harlequin/issues/432):
    # `short_decls=["-t", "--token"]`
)

username = TextOption(
    name="username",
    description="Your Databricks user account's username (if using basic authentication)",
    # 2024/01/28 Alex Malins: disabling these short_decls due to conflict with other adapters:
    # (https://github.com/tconbeer/harlequin/issues/432):
    # `short_decls=["-u", "--user", "-U"]`
)

password = TextOption(
    name="password",
    description="Your Databricks user account's password (if using basic authentication)",
)

auth_type = SelectOption(
    name="auth-type",
    description=(
        "Set to `databricks-oauth` or `azure-oauth` if using OAuth user-to-machine (U2M) "
        "authentication"
    ),
    choices=["databricks-oauth", "azure-oauth"],
)

skip_legacy_indexing = FlagOption(
    name="skip-legacy-indexing",
    description=(
        "Skip the indexing of legacy metastores (e.g. `hive_metastore`). Set this flag if your "
        "Databricks instance runs Unity Catalog and you do not want the overhead of slow indexing "
        "of assets in legacy metastores - i.e. you do not mind them not appearing in Harlequin's "
        "Data Catalog pane."
    ),
)

client_id = TextOption(
    name="client-id",
    description=(
        "Service principal's UUID or Application ID for OAuth machine-to-machine (M2M) "
        "authentication. To use OAuth M2M you need to install `databricks-sdk` as an extra into "
        "your python environment."
    ),
)

client_secret = TextOption(
    name="client-secret",
    description=(
        "Service principal's secrete for OAuth when using OAuth machine-to-machine (M2M) "
        "authentication. To use OAuth M2M you need to install `databricks-sdk` as an extra into "
        "your python environment."
    ),
)

init_path = PathOption(
    name="init-path",
    description=(
        "The path to an initialization script. On startup, Harlequin will execute "
        "the commands in the script against the attached database."
    ),
    short_decls=["-i", "-init"],
    exists=False,
    file_okay=True,
    dir_okay=False,
    resolve_path=True,
    path_type=Path,
)

no_init = FlagOption(
    name="no-init",
    description="Start Harlequin without executing the initialization script.",
)

DATABRICKS_ADAPTER_OPTIONS = [
    server_hostname,
    http_path,
    access_token,
    username,
    password,
    auth_type,
    skip_legacy_indexing,
    client_id,
    client_secret,
    init_path,
    no_init,
]
