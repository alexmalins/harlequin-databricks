from __future__ import annotations

import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Databricks's SQL keywords page was last updated October 10, 2023. It is archived at:
# https://web.archive.org/web/20240122080239/https://docs.databricks.com/en/sql/language-manual/sql-ref-reserved-words.html
URL = "https://docs.databricks.com/en/sql/language-manual/sql-ref-reserved-words.html"


def scrape_keywords() -> list[str]:
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    results = soup.find_all(
        id=[  # These id tag sections of page contain all keywords
            "reserved-words",
            "special-words-in-expressions",
            "reserved-catalog-names",
            "reserved-schema-names",
            "ansi-reserved-words",
        ]
    )

    keywords = []
    for result in results:
        keywords += [  # Look for uppercase keywords, 2+ chars long
            keyword.strip(",")
            for keyword in result.text.split()
            if keyword.isupper() and len(keyword) > 1 and "`" not in keyword
        ]

    keywords += ["LIMIT"]  # Add keywords missing from Databricks page for some reason
    keywords = sorted(list(set(keywords)))
    manual_remove = ["ANSI", "CURRENT_", "SQL", "SQL2016"]  # Drop these non-keywords
    keywords = [keyword for keyword in keywords if keyword not in manual_remove]

    return keywords


def main() -> None:
    keywords = scrape_keywords()

    # Overwrite file in ../src/harlequin_databricks/keywords.csv
    # creating it if it doesn't exist
    path = Path(__file__).parents[1] / "src" / "harlequin_databricks" / "keywords.csv"
    with path.open("w+", encoding="utf-8") as file:
        writer = csv.writer(file, delimiter="\n")
        writer.writerow(keywords)


if __name__ == "__main__":
    main()
