#!/usr/bin/env python3
"""Send prompts from output.txt to a local completions endpoint."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


DEFAULT_URL = "http://localhost:9000/v1/completions"


def decode_raw_json_string(raw_prompt: str) -> str:
    """Decode one line produced by extract_inputs.py back to the original prompt."""
    return json.loads(f'"{raw_prompt}"')


def load_prompts(path: Path, request_count: int | None) -> list[str]:
    raw_prompts = path.read_text(encoding="utf-8").splitlines()
    if request_count is not None:
        raw_prompts = raw_prompts[:request_count]

    prompts = []
    for line_number, raw_prompt in enumerate(raw_prompts, start=1):
        try:
            prompts.append(decode_raw_json_string(raw_prompt))
        except json.JSONDecodeError as error:
            raise ValueError(f"Failed to decode prompt on line {line_number}: {error}") from error
    return prompts


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value must be 0 or greater")
    return number


def build_payload(
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    return json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        ensure_ascii=False,
    )


def run_curl(url: str, payload: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "curl",
            url,
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
            "--max-time",
            str(timeout),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def write_response(response_file: Path, index: int, result: subprocess.CompletedProcess[str]) -> None:
    record = {
        "index": index,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    with response_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read prompts from output.txt and send curl requests to /v1/completions."
    )
    parser.add_argument(
        "input_txt",
        type=Path,
        nargs="?",
        default=Path("output.txt"),
        help="Path to output.txt. Default: output.txt",
    )
    parser.add_argument(
        "-n",
        "--num-requests",
        type=non_negative_int,
        help="Number of requests to send. Default: send all prompts.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Endpoint URL. Default: {DEFAULT_URL}")
    parser.add_argument("--model", default="vllm_infer", help="Model name. Default: vllm_infer")
    parser.add_argument("--max-tokens", type=int, default=100, help="max_tokens value. Default: 100")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0,
        help="temperature value. Default: 0",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="curl --max-time timeout in seconds. Default: 300",
    )
    parser.add_argument(
        "--response-file",
        type=Path,
        help="Optional JSONL file to save curl stdout/stderr for each request.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print request payloads without calling curl.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prompts = load_prompts(args.input_txt, args.num_requests)

    if args.response_file:
        args.response_file.write_text("", encoding="utf-8")

    for index, prompt in enumerate(prompts, start=1):
        payload = build_payload(
            prompt=prompt,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        if args.dry_run:
            print(payload)
            continue

        print(f"Sending request {index}/{len(prompts)}")
        result = run_curl(args.url, payload, args.timeout)

        if args.response_file:
            write_response(args.response_file, index, result)
        else:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)

        if result.returncode != 0:
            raise SystemExit(f"curl failed for request {index} with code {result.returncode}")


if __name__ == "__main__":
    main()
