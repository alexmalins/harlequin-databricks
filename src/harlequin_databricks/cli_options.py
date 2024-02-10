from harlequin.options import FlagOption, SelectOption, TextOption

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
    description="Set to `databricks-oauth` if using OAuth user-to-machine (U2M) authentication",
    choices=["databricks-oauth"],
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

DATABRICKS_ADAPTER_OPTIONS = [
    server_hostname,
    http_path,
    access_token,
    username,
    password,
    auth_type,
    skip_legacy_indexing,
]
