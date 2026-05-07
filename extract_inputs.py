#!/usr/bin/env python3
"""Extract raw JSON string contents for fields named "input" to a text file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_json_string(source: str, start: int) -> tuple[str, str, int]:
    """Return the decoded string, raw content, and end offset for a JSON string."""
    if start >= len(source) or source[start] != '"':
        raise ValueError(f"Expected JSON string at offset {start}.")

    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "\\":
            index += 2
            continue
        if char == '"':
            literal = source[start : index + 1]
            return json.loads(literal), source[start + 1 : index], index + 1
        index += 1

    raise ValueError(f"Unterminated JSON string at offset {start}.")


def skip_whitespace(source: str, start: int) -> int:
    while start < len(source) and source[start].isspace():
        start += 1
    return start


def extract_raw_input_values(source: str) -> list[str]:
    """Extract raw contents inside quotes for every JSON key named input."""
    values: list[str] = []
    index = 0

    while index < len(source):
        if source[index] != '"':
            index += 1
            continue

        key, _raw_key, end = parse_json_string(source, index)
        colon = skip_whitespace(source, end)
        if colon >= len(source) or source[colon] != ":":
            index = end
            continue

        value_start = skip_whitespace(source, colon + 1)
        if key == "input" and value_start < len(source) and source[value_start] == '"':
            _value, raw_value, value_end = parse_json_string(source, value_start)
            values.append(raw_value)
            index = value_end
            continue

        index = value_start

    return values


def write_inputs(input_values: list[str], output_path: Path) -> int:
    output_path.write_text("\n".join(input_values), encoding="utf-8")
    return len(input_values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            'Extract raw quoted contents of all JSON fields named "input" to a txt file.'
        )
    )
    parser.add_argument("json_file", type=Path, help="Path to the source JSON/JSONL file.")
    parser.add_argument("txt_file", type=Path, help="Path to the output txt file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.json_file.read_text(encoding="utf-8")
    count = write_inputs(extract_raw_input_values(source), args.txt_file)
    print(f"Wrote {count} input value(s) to {args.txt_file}")


if __name__ == "__main__":
    main()
