from __future__ import annotations

import re


TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def public_alias(slug: str, original_name: str) -> str:
    if not TOOL_NAME_RE.fullmatch(original_name):
        raise ValueError("upstream tool name must match [A-Za-z0-9._-]{1,128}")
    return f"{slug}__{original_name}"
