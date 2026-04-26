from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent / "world_locations.json.gz"


@lru_cache(maxsize=1)
def load_world_locations() -> list[dict]:
    with gzip.open(DATA_PATH, "rt", encoding="utf-8") as file_handle:
        return json.load(file_handle)


@lru_cache(maxsize=1)
def get_all_countries() -> list[dict[str, str]]:
    countries = []
    for country in load_world_locations():
        countries.append(
            {
                "name": (country.get("name") or "").strip(),
                "iso2": (country.get("iso2") or "").strip(),
            }
        )
    return sorted(countries, key=lambda entry: entry["name"])


def get_country(country_name: str) -> dict | None:
    normalized_name = (country_name or "").strip().casefold()
    if not normalized_name:
        return None
    for country in load_world_locations():
        if (country.get("name") or "").strip().casefold() == normalized_name:
            return country
    return None


def get_states_of_country(country_name: str) -> list[str]:
    country = get_country(country_name)
    if not country:
        return []
    states = []
    for state in country.get("states") or []:
        name = (state.get("name") or "").strip()
        if name and name not in states:
            states.append(name)
    return sorted(states)


@lru_cache(maxsize=1)
def get_country_states_map() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for country in load_world_locations():
        country_name = (country.get("name") or "").strip()
        if not country_name:
            continue
        states: list[str] = []
        for state in country.get("states") or []:
            state_name = (state.get("name") or "").strip()
            if state_name and state_name not in states:
                states.append(state_name)
        mapping[country_name] = sorted(states)
    return mapping


@lru_cache(maxsize=1)
def get_all_states() -> list[str]:
    states: list[str] = []
    for country_states in get_country_states_map().values():
        for state_name in country_states:
            if state_name not in states:
                states.append(state_name)
    return sorted(states)


def get_districts_of_state(country_name: str, state_name: str) -> list[str]:
    country = get_country(country_name)
    if not country:
        return []
    normalized_state = (state_name or "").strip().casefold()
    if not normalized_state:
        return []
    for state in country.get("states") or []:
        if (state.get("name") or "").strip().casefold() != normalized_state:
            continue
        districts = []
        for city in state.get("cities") or []:
            name = (city.get("name") or "").strip()
            if name and name not in districts:
                districts.append(name)
        return sorted(districts)
    return []
