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
for game in games:
    recap_url = game.get("recapUrl")
    if recap_url:
        assert recap_url.startswith("https://www.youtube.com/watch?v="), "Recaps must use canonical YouTube URLs"
        assert game.get("kickoff"), "A recap must belong to a scheduled game"
regular = [game for game in games if game.get("seasonType") == "regular"]
preseason = [game for game in games if game.get("seasonType") == "preseason"]
assert payload.get("gameCount") == len(games) == 321, "Expected all 321 scheduled games"
assert len(regular) == 272, "Expected all 272 regular-season games"
assert len(preseason) == 49, "Expected all 49 preseason games"
assert {game["week"] for game in regular} == set(range(1, 19)), "Expected regular weeks 1–18"
assert {game["week"] for game in preseason} == set(range(1, 5)), "Expected all preseason weeks"
print("Spoiler check passed: 321 games, 22 schedule weeks, 0 result-bearing fields")
