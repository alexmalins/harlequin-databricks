from __future__ import annotations

import csv
from pathlib import Path

from harlequin import HarlequinCompletion


def load_completions() -> list[HarlequinCompletion]:
    completions: list[HarlequinCompletion] = []

    keywords_path = Path(__file__).parent / "keywords.csv"
    with keywords_path.open("r") as file:
        reader = csv.reader(file, dialect="unix")
        for name in reader:
            completions.append(
                HarlequinCompletion(
                    label=name[0].lower(),
                    type_label="kw",
                    value=name[0].lower(),
                    priority=1000,
                    context=None,
                )
            )

    functions_path = Path(__file__).parent / "functions.csv"
    with functions_path.open("r") as file:
        reader = csv.reader(file, dialect="unix")
        next(reader)  # Skip header row
        for name, _, _ in reader:
            completions.append(
                HarlequinCompletion(
                    label=name.lower(),
                    type_label="fn",
                    value=name.lower(),
                    priority=1000,
                    context=None,
                )
            )

    return completions
