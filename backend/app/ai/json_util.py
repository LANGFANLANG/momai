from __future__ import annotations

import json
import re


class LlmError(ValueError):
    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


class LlmJsonError(LlmError):
    pass


def strip_json_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return text
    return text[start : end + 1]


def remove_trailing_commas(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def insert_missing_commas(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    escape = False
    after_value = False

    def take_literal(literal: str) -> bool:
        nonlocal i, after_value
        if not text.startswith(literal, i):
            return False
        end = i + len(literal)
        if end < n and (text[end].isalnum() or text[end] == "_"):
            return False
        out.append(literal)
        i = end
        after_value = True
        return True

    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
                after_value = True
            i += 1
            continue

        if ch.isspace():
            out.append(ch)
            i += 1
            continue

        if after_value:
            if ch in ",}]":
                after_value = ch in "}]"
                out.append(ch)
                i += 1
                continue
            if ch in '"{[tfn0123456789-':
                out.append(",")
                after_value = False
                continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch in "{[":
            after_value = False
            out.append(ch)
            i += 1
            continue

        if ch in "}]":
            after_value = True
            out.append(ch)
            i += 1
            continue

        if ch in ",:":
            after_value = False
            out.append(ch)
            i += 1
            continue

        if take_literal("true") or take_literal("false") or take_literal("null"):
            continue

        number = re.match(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text[i:])
        if number:
            out.append(number.group(0))
            i += len(number.group(0))
            after_value = True
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def loads_llm_json(text: str) -> dict:
    candidate = extract_json_object(strip_json_fences(text))
    attempts = [
        candidate,
        remove_trailing_commas(candidate),
        insert_missing_commas(remove_trailing_commas(candidate)),
    ]
    last_error: json.JSONDecodeError | None = None
    seen: set[str] = set()
    for attempt in attempts:
        if attempt in seen:
            continue
        seen.add(attempt)
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if isinstance(parsed, dict):
            return parsed
        raise LlmJsonError("模型返回的 JSON 必须是对象", text)
    raise LlmJsonError("模型返回的内容不是合法 JSON，请再试一次。", text) from last_error
