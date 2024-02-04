from harlequin.options import SelectOption, TextOption

server_hostname = TextOption(
    name="server_hostname",
    description="Databricks instance server hostname (ex. ****.cloud.databricks.com)",
    short_decls=["--server-hostname"],
)

http_path = TextOption(
    name="http_path",
    description=(
        "HTTP path of either a Databricks SQL warehouse (ex. /sql/1.0/endpoints/1234567890abcdef)"
        "or a Databricks runtime interactive cluster (ex. "
        "/sql/protocolv1/o/1234567890123456/1234-123456-slid123)"
    ),
    short_decls=["--http-path"],
    # 2024/01/28 Alex Malins: disabling these short_decls due to conflict with other adapters
    # (https://github.com/tconbeer/harlequin/issues/432ß):
    # `"-p", "--path"`
)

access_token = TextOption(
    name="access_token",
    description="Your Databricks personal access token (if using PAT authentication)",
    short_decls=["--access-token"],
    # 2024/01/28 Alex Malins: disabling these short_decls due to conflict with other adapters
    # (https://github.com/tconbeer/harlequin/issues/432):
    # `"-t", "--token"`
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
    name="auth_type",
    description="Set to `databricks-oauth` if using OAuth user-to-machine (U2M) authentication",
    choices=["databricks-oauth"],
    short_decls=["--auth-type"],
)

DATABRICKS_ADAPTER_OPTIONS = [
    server_hostname,
    http_path,
    access_token,
    username,
    password,
    auth_type,
]
