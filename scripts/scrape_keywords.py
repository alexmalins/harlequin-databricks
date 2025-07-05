from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Databricks's SQL keywords page was last updated October 10, 2023. It is archived at:
# https://web.archive.org/web/20250705123402/https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-reserved-words
URL = "https://docs.databricks.com/en/sql/language-manual/sql-ref-reserved-words"

# Add keyword missing from Databricks page for some reason
MANUAL_ADD = ["LIMIT"]

# Drop these non-keywords that are scraped from the page
MANUAL_REMOVE = [
    "'ANTI'>",
    "(NULL",
    "(SELECT",
    "(VALUES",
    "ANSI",
    "CURRENT_",
    "DEFAULT)",
    "NULL>",
    "SQL",
    "SQL--",
    "SQL2016",
    "VALUES(1)",
]


def scrape_keywords() -> list[str]:
    page = requests.get(URL, timeout=10)
    soup = BeautifulSoup(page.content, "html.parser")

    results = soup.find_all("div", class_="theme-doc-markdown markdown")

    keywords = []
    for result in results:
        keywords += [  # Look for uppercase keywords, 2+ chars long
            keyword.strip(",")
            for keyword in result.text.split()
            if keyword.isupper() and len(keyword) > 1 and "`" not in keyword
        ]

    keywords += MANUAL_ADD  # Add keywords missing from Databricks page for some reason
    keywords = sorted(set(keywords))
    return [keyword for keyword in keywords if keyword not in MANUAL_REMOVE]


def main() -> None:
    keywords = scrape_keywords()

    # Overwrite file in ../src/harlequin_databricks/keywords.csv
    # creating it if it doesn't exist
    path = Path(__file__).parents[1] / "src" / "harlequin_databricks" / "keywords.csv"
    with path.open("w+", encoding="utf-8") as file:
        file.write("\n".join(keywords))


if __name__ == "__main__":
    main()
