#!/usr/bin/env python3
"""Export all rows from a DynamoDB table to UTF-8 JSON (handles emoji on Windows)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


def export_dynamodb_table(
    table_name: str = "yougov-ai-table",
    region: str = "eu-central-1",
    output: str | Path | None = None,
) -> Path:
    out_path = Path(output) if output is not None else Path(f"{table_name}-export.json")

    client = boto3.client("dynamodb", region_name=region)
    paginator = client.get_paginator("scan")
    items = []
    for page in paginator.paginate(TableName=table_name):
        items.extend(page.get("Items", []))

    payload = {"TableName": table_name, "ItemCount": len(items), "Items": items}
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(items)} items to {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-name", default="yougov-ai-table")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path (default: <table-name>-export.json)",
    )
    args = parser.parse_args()
    export_dynamodb_table(
        table_name=args.table_name,
        region=args.region,
        output=args.output,
    )


if __name__ == "__main__":
    main()
