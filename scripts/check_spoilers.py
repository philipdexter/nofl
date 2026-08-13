#!/usr/bin/env python3
"""Fail if result-bearing fields leak into the public schedule bundle."""

import json
import pathlib
import sys


SCHEDULE = pathlib.Path(__file__).resolve().parents[1] / "data" / "schedule.json"
FORBIDDEN_KEYS = {
    "score",
    "scores",
    "winner",
    "record",
    "records",
    "status",
    "completed",
    "result",
    "results",
    "gamecast",
    "recap",
}


def walk(value, path="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in FORBIDDEN_KEYS:
                yield f"{path}.{key}"
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


payload = json.loads(SCHEDULE.read_text(encoding="utf-8"))
leaks = list(walk(payload))
if leaks:
    print("Spoiler-bearing fields found:", *leaks, sep="\n  ", file=sys.stderr)
    raise SystemExit(1)

games = payload.get("games", [])
assert payload.get("gameCount") == len(games) == 272, "Expected all 272 regular-season games"
assert {game["week"] for game in games} == set(range(1, 19)), "Expected weeks 1–18"
print("Spoiler check passed: 272 games, 18 weeks, 0 result-bearing fields")

