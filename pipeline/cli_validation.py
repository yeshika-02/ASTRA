"""Argument validators for the pipeline's command-line entry points (SP-25).

Each function is an argparse ``type=``: it returns the converted value or raises
argparse.ArgumentTypeError with a message that names the problem, so a bad value stops
the script immediately ("usage: ... error: argument --workers: must be at least 1, got 0")
instead of failing later with an unrelated error.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from data.labels import NAME_TO_LABEL


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a whole number, got {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def non_negative_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"must be a whole number, got {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or more, got {value}")
    return value


def astra_class(text: str) -> str:
    if text not in NAME_TO_LABEL:
        raise argparse.ArgumentTypeError(f"unknown class {text!r}; choose from {', '.join(NAME_TO_LABEL)}")
    return text


def existing_dir(text: str) -> Path:
    path = Path(text)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"directory not found: {path}")
    return path


def existing_file(text: str) -> Path:
    path = Path(text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"file not found: {path}")
    return path
