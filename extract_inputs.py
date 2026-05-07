#!/usr/bin/env python3
"""Extract all JSON values named "input" and write them to a text file."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def load_json_records(path: Path) -> Any:
    """Load a JSON file, falling back to JSON Lines when needed."""
    text = path.read_text(encoding="utf-8")

    try:
        return json.loads(text)
    except json.JSONDecodeError as original_error:
        records = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as line_error:
                raise ValueError(
                    f"{path} is neither valid JSON nor JSON Lines. "
                    f"Failed at line {line_number}: {line_error}"
                ) from original_error
        return records


def iter_input_values(data: Any) -> Iterable[str]:
    """Yield string values for every key named input in nested JSON data."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "input":
                yield str(value)
            else:
                yield from iter_input_values(value)
    elif isinstance(data, list):
        for item in data:
            yield from iter_input_values(item)


def write_inputs(input_values: Iterable[str], output_path: Path, separator: str) -> int:
    values = list(input_values)
    output_path.write_text(separator.join(values), encoding="utf-8")
    return len(values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Extract values of all JSON fields named "input" to a txt file.'
    )
    parser.add_argument("json_file", type=Path, help="Path to the source JSON/JSONL file.")
    parser.add_argument("txt_file", type=Path, help="Path to the output txt file.")
    parser.add_argument(
        "--separator",
        default="\n\n",
        help=r"Text placed between extracted inputs. Default: blank line.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_json_records(args.json_file)
    count = write_inputs(iter_input_values(data), args.txt_file, args.separator)
    print(f"Wrote {count} input value(s) to {args.txt_file}")


if __name__ == "__main__":
    main()
