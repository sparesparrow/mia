from __future__ import annotations

import json
from typing import Any


def _strip_comments(text: str) -> tuple[str, int]:
    out: list[str] = []
    in_string = False
    escape = False
    removed = 0
    quote = ""
    i = 0
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                in_string = False
            i += 1
            continue
        if char in ('"', "'"):
            in_string = True
            quote = char
            out.append(char)
            i += 1
            continue
        if char == "/" and i + 1 < len(text):
            next_char = text[i + 1]
            if next_char == "/":
                removed += 1
                i += 2
                while i < len(text) and text[i] not in "\r\n":
                    i += 1
                continue
            if next_char == "*":
                removed += 1
                i += 2
                while i + 1 < len(text) and text[i : i + 2] != "*/":
                    i += 1
                i += 2
                continue
        out.append(char)
        i += 1
    return "".join(out), removed


def _strip_trailing_commas(text: str) -> tuple[str, int]:
    out: list[str] = []
    in_string = False
    escape = False
    quote = ""
    removed = 0
    i = 0
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                in_string = False
            i += 1
            continue
        if char in ('"', "'"):
            in_string = True
            quote = char
            out.append(char)
            i += 1
            continue
        if char == ",":
            lookahead = i + 1
            while lookahead < len(text) and text[lookahead] in " \t\r\n":
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                removed += 1
                i += 1
                continue
        out.append(char)
        i += 1
    return "".join(out), removed


def parse_jsonc(text: str) -> tuple[Any, list[str]]:
    notes: list[str] = []
    cleaned = text.lstrip("\ufeff")
    without_comments, comment_count = _strip_comments(cleaned)
    if comment_count:
        notes.append(f"Removed {comment_count} JSONC comment block(s) before parsing")
    without_trailing_commas, comma_count = _strip_trailing_commas(without_comments)
    if comma_count:
        notes.append(f"Removed {comma_count} trailing comma(s) before parsing")
    return json.loads(without_trailing_commas), notes
