"""Tests fuer Katalog (docs/03, Abschnitt 9) und Baukasten (Abschnitt 10)."""

from __future__ import annotations

import importlib.util
import json
import random
from math import gcd
from pathlib import Path

import pytest

from waagenspiel.catalog import DEFAULT_PATH, CatalogSource, example_weights, load_catalog
from waagenspiel.construct import ConstructiveGenerator, Knowledge
from waagenspiel.puzzle import (
    LEVELS,
    PuzzleGenerator,
    Scale,
    Settings,
    canonical_form,
    forces_lighter,
    forces_lighter_z3,
    heaviest,
    is_minimal,
    level_of,
    solve,
)

ROOT = Path(__file__).resolve().parents[1]
needs_catalog = pytest.mark.skipif(not DEFAULT_PATH.exists(), reason="data/katalog.json.gz fehlt")


def scales(*texts: str) -> list[Scale]:
    return [Scale.parse(t) for t in texts]


# --- Bausteinregel ----------------------------------------------------------


def test_rule_finds_chains() -> None:
    knowledge = Knowledge()
    knowledge.learn(scales("b + c < a", "2d < a + c"))
    assert {(1, 0), (2, 0), (3, 0)} <= knowledge.lt


def test_blocks_are_needed_for_sum_substitution() -> None:
    system = scales("c + d < a", "2b < a + c + d")
    without = Knowledge()
    without.learn(system)
    assert (1, 0) not in without.lt
    with_blocks = Knowledge(use_blocks=True)
    with_blocks.learn(system)
    assert (1, 0) in with_blocks.lt


def test_balance_of_single_items_is_not_strict() -> None:
    knowledge = Knowledge()
    knowledge.learn(scales("b = c", "c < a"))
    assert (1, 2) in knowledge.le and (1, 2) not in knowledge.lt
    assert (1, 0) in knowledge.lt


def test_rule_is_sound_against_the_exact_test() -> None:
    """Was die Regel folgert, muss auch exakt folgen."""

    generator = PuzzleGenerator(Settings(scale_counts=(3,), max_side=3), seed=2)
    rng = random.Random(2)
    checked = 0
    while checked < 40:
        weights = generator._weights()
        from waagenspiel.puzzle import true_scales

        tilted, balanced = true_scales(weights, 3)
        system = rng.sample(tilted + balanced, 3)
        knowledge = Knowledge(use_blocks=True)
        knowledge.learn(system)
        for x, h in knowledge.lt:
            assert forces_lighter(system, x, h), (system, x, h)
        checked += 1


# --- Baukasten ----------------------------------------------------------------


@pytest.mark.parametrize("level", [1, 2, 3])
def test_construction_hits_exact_levels(level: int) -> None:
    settings = Settings(scale_counts=(2, 3), max_side=3, min_difficulty=level, max_difficulty=level)
    puzzles = list(ConstructiveGenerator(settings, seed=level).generate(3))
    for puzzle in puzzles:
        assert puzzle.difficulty == level == level_of(list(puzzle.scales), top=0)
        assert heaviest(list(puzzle.scales)) == 0
        assert is_minimal(list(puzzle.scales))
        assert canonical_form(list(puzzle.scales))[1] == puzzle.scales
        assert all(s.holds(puzzle.weights) for s in puzzle.scales)
    assert len({p.scales for p in puzzles}) == len(puzzles)


def test_construction_respects_single_item_sides() -> None:
    for puzzle in ConstructiveGenerator(LEVELS["leicht"], seed=4).generate(3):
        assert all(sum(s.left) == sum(s.right) == 1 for s in puzzle.scales)
        assert puzzle.difficulty <= 2


def test_construction_refuses_level_four() -> None:
    with pytest.raises(ValueError):
        ConstructiveGenerator(LEVELS["experte"])


# --- Stufen schnell und exakt -----------------------------------------------


def test_level_of_matches_solve() -> None:
    for texts in [
        ("b + c < a", "d < a"),
        ("d < c", "c < b", "b < a"),
        ("2d < 3c", "3b < c + d", "2a = 3c"),
        ("c + 2d < 2a + b", "b + 2d = 3c", "a + b + c = 3d"),
    ]:
        system = scales(*texts)
        assert level_of(system, top=0, entails=forces_lighter_z3) == level_of(system) == solve(system).level


def test_example_weights_are_small_and_valid() -> None:
    system = scales("c + 2d < 2a + b", "b + 2d = 3c", "a + b + c = 3d")
    weights = example_weights(system)
    assert all(s.holds(weights) for s in system)
    assert sum(weights) <= 16  # (8, 1, 3, 4) waere eine Loesung mit Summe 16


# --- Katalog ------------------------------------------------------------------


@pytest.fixture(scope="module")
def catalog() -> dict:
    return load_catalog()


@needs_catalog
def test_catalog_counts(catalog: dict) -> None:
    entries = catalog["puzzles"]
    assert catalog["metadata"]["count"] == len(entries) == 147_462
    assert sum(len(e) == 3 for e in entries) == 669
    assert sum(len(e) == 4 for e in entries) == 146_793
    without_multiples = [
        e for e in entries if all(gcd(*s.left, *s.right) == 1 for s in map(Scale.parse, e[:-1]))
    ]
    assert len(without_multiples) == 617 + 115_158


@needs_catalog
def test_catalog_entries_are_valid(catalog: dict) -> None:
    rng = random.Random(1)
    for entry in rng.sample(catalog["puzzles"], 60):
        system = [Scale.parse(t) for t in entry[:-1]]
        assert heaviest(system) == 0
        assert is_minimal(system)
        assert canonical_form(system)[1] == tuple(system)
        assert level_of(system, top=0) == entry[-1]


@needs_catalog
def test_generated_puzzles_are_in_the_catalog(catalog: dict) -> None:
    known = {tuple(e[:-1]): e[-1] for e in catalog["puzzles"]}
    for generator in (
        PuzzleGenerator(LEVELS["mittel"], seed=12),
        ConstructiveGenerator(LEVELS["schwer"], seed=12),
    ):
        for puzzle in generator.generate(3):
            assert known[tuple(map(str, puzzle.scales))] == puzzle.difficulty


@needs_catalog
def test_catalog_source_filters() -> None:
    source = CatalogSource(LEVELS["experte"], seed=3)
    puzzle = next(source.generate(1))
    assert puzzle.difficulty == 4 and len(puzzle.scales) == 3
    assert all(gcd(*s.left, *s.right) == 1 for s in puzzle.scales)
    assert all(s.holds(puzzle.weights) for s in puzzle.scales)
    single = CatalogSource(LEVELS["leicht"], seed=3)
    assert all(max(sum(s.left), sum(s.right)) == 1 for s, in [(p.scales[0],) for p in single.generate(3)])


# --- Kommandozeile ---------------------------------------------------------------


def _cli():
    spec = importlib.util.spec_from_file_location("raetsel", ROOT / "raetsel.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("source", ["baukasten", pytest.param("katalog", marks=needs_catalog)])
def test_cli_sources(source: str, tmp_path: Path) -> None:
    target = tmp_path / "r.json"
    args = ["erzeugen", "--anzahl", "2", "--stufe", "schwer", "--quelle", source, "--seed", "5", "--ausgabe", str(target)]
    assert _cli().main(args) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["metadata"]["puzzle_source"] == source
    assert all(p["difficulty"] == 3 for p in data["puzzles"])
