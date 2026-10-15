"""Run the real two-turn T-003 tool-calling check."""

from __future__ import annotations

import json
import time

from provider import ResponsesProvider, validate_arguments


TOOLS = [
    {
        "type": "function",
        "name": "lookup_inventory",
        "description": "Return fake inventory for a named product.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"product": {"type": "string"}},
            "required": ["product"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "draft_product",
        "description": "Create a harmless preview only; it never persists data.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"},
            },
            "required": ["name", "price"],
            "additionalProperties": False,
        },
    },
]


def fake_execute(name: str, arguments: dict[str, object]) -> dict[str, object]:
    if name == "lookup_inventory":
        return {"product": arguments["product"], "quantity": 7}
    if name == "draft_product":
        return {"preview": arguments, "persisted": False}
    raise ValueError(f"unknown tool: {name}")


def main() -> None:
    provider = ResponsesProvider.from_env()
    conversation: list[dict[str, object]] = [
        {
            "role": "user",
            "content": (
                "First call lookup_inventory for 'Demo mug'. After receiving that "
                "result, call draft_product for a 'Demo mug' priced 12.5. After "
                "receiving that result, state the inventory and whether the draft "
                "was persisted. Do not skip either tool."
            ),
        }
    ]
    started = time.perf_counter()
    expected = {"lookup_inventory", "draft_product"}
    seen_names: set[str] = set()
    seen_ids: set[str] = set()
    final_text = ""
    turns = 0
    for turns in range(1, 5):
        completion = provider.get_completion(conversation, TOOLS)
        conversation.extend(completion.output_items)
        if not completion.calls:
            final_text = completion.text.strip()
            break
        for call in completion.calls:
            if call.id in seen_ids:
                raise RuntimeError(f"provider repeated tool call ID {call.id}")
            tool = next((item for item in TOOLS if item["name"] == call.name), None)
            if tool is None:
                raise RuntimeError(f"provider requested unknown tool {call.name}")
            validate_arguments(call.arguments, tool["parameters"])
            seen_ids.add(call.id)
            seen_names.add(call.name)
            conversation.append(
                {
                    "type": "function_call_output",
                    "call_id": call.id,
                    "output": json.dumps(fake_execute(call.name, call.arguments)),
                }
            )

    if seen_names != expected:
        raise RuntimeError(f"expected calls {sorted(expected)}, got {sorted(seen_names)}")
    if not final_text:
        raise RuntimeError("provider did not return final text after tool results")
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    print(f"PASS provider=GroqCloud model={provider.model} calls={len(seen_ids)} turns={turns} elapsed_ms={elapsed_ms}")
    print(final_text)


if __name__ == "__main__":
    main()
