from pathlib import Path

import pandas as pd

# Last run with Databricks's SQL functions page updated on August 2, 2024. This is archived at:
# https://web.archive.org/web/20240804040816/https://docs.databricks.com/en/sql/language-manual/sql-ref-functions-builtin.html
URL = (
    "https://docs.databricks.com/en/sql/language-manual/sql-ref-functions-builtin.html"
)


def scrape_functions_and_descriptions() -> pd.DataFrame:
    # Read HTML tables containing functions into DataFrame
    tables = pd.read_html(URL)
    function_tables = [
        table[["Function", "Description"]]
        for table in tables
        if "Function" in table.columns and "Description" in table.columns
    ]
    combined = pd.concat(function_tables)

    # Remove operators and expressions, then de-dupe
    functions_only = combined[
        (combined["Function"].str.contains("\\("))
        & (combined["Function"].str.contains("\\)"))
    ].copy()
    functions_only["Name"] = functions_only["Function"].str.split("(").str[0]
    deduped = functions_only.groupby("Name").first()

    return deduped


def main() -> None:
    functions = scrape_functions_and_descriptions()

    # Overwrite file in ../src/harlequin_databricks/functions.csv
    # creating it if it doesn't exist
    path = Path(__file__).parents[1] / "src" / "harlequin_databricks" / "functions.csv"
    functions.to_csv(path, encoding="utf-8")


if __name__ == "__main__":
    main()
