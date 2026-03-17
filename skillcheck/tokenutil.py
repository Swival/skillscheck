from __future__ import annotations

import tiktoken

_enc: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _enc
    if _enc is None:
        _enc = tiktoken.get_encoding("cl100k_base")
    return _enc


def count_tokens(text: str) -> int:
    return len(_get_encoder().encode(text))


def estimate_file_tokens(path: str) -> int | None:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return count_tokens(content)
    except OSError:
        return None
