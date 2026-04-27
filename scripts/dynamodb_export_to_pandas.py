#!/usr/bin/env python3
"""Load a JSON file from export_dynamodb_table.py into a pandas DataFrame."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from boto3.dynamodb.types import TypeDeserializer


def load_dynamodb_export_json(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "Items" in data:
        items = data["Items"]
    else:
        raise ValueError(
            "Expected a list of items or a dict with an 'Items' key (export_dynamodb_table.py format)."
        )

    deserializer = TypeDeserializer()
    rows = [
        {k: deserializer.deserialize(v) for k, v in item.items()} for item in items
    ]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "json_path",
        type=Path,
        help="Path to UTF-8 JSON from export_dynamodb_table.py",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional path to write CSV (UTF-8)",
    )
    args = parser.parse_args()

    df = load_dynamodb_export_json(args.json_path)
    print(df.info())
    print(df.head())

    if args.output is not None:
        df.to_csv(args.output, index=False, encoding="utf-8")
        print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
