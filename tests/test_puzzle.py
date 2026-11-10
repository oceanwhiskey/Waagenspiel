"""Tests fuer docs/03_einfache_herleitung.md und src/waagenspiel/puzzle.py."""

from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path

import pytest

from waagenspiel.puzzle import (
    LEVELS,
    LOWER_PERMUTATIONS,
    Derivation,
    PuzzleGenerator,
    Scale,
    Settings,
    canonical_form,
    derive,
    explain,
    heaviest,
    is_minimal,
    satisfiable,
)

ROOT = Path(__file__).resolve().parents[1]


def scales(*texts: str) -> list[Scale]:
    return [Scale.parse(text) for text in texts]


def assert_valid(derivation: Derivation) -> None:
    """Satz 2: Σ count·(L - R) - factor·(e_lighter - e_heavier) >= 0."""

    rest = [0, 0, 0, 0]
    for use in derivation.uses:
        assert use.count > 0
        for i in range(4):
            rest[i] += use.count * (use.left[i] - use.right[i])
    rest[derivation.lighter] -= derivation.factor
    rest[derivation.heavier] += derivation.factor
    assert all(value >= 0 for value in rest), rest
    assert derivation.steps()[-1].endswith(".")


# --- Normalform --------------------------------------------------------------


def test_scale_is_cancelled_and_oriented() -> None:
    assert Scale.parse("a + b < b + c") == Scale.parse("a < c")
    assert Scale.parse("c > a") == Scale.parse("a < c")
    assert Scale.parse("b + c = a") == Scale.parse("a = b + c")
    assert str(Scale.parse("2a + c > 3d")) == "3d < 2a + c"


def test_multiples_are_not_divided() -> None:
    assert Scale.parse("2a < 2b") != Scale.parse("a < b")


@pytest.mark.parametrize("text", ["a + b + c + d < a", "a = a", "a + b < a + b", "e < a"])
def test_invalid_scales_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        Scale.parse(text)


# --- Satz 1 -------------------------------------------------------------------


def test_example_from_the_derivation() -> None:
    system = scales("3d < 2a + c", "b + c < a")
    assert heaviest(system) == 0
    assert is_minimal(system)
    derivations = explain(system)
    for derivation in derivations:
        assert_valid(derivation)
    by_name = {d.lighter: d for d in derivations}
    assert by_name[3].steps() == [
        "Waage 1: 3d < 2a + c",
        "Waage 2: b + c < a",
        "Zusammen: b + c + 3d < 3a + c",
        "Auf beiden Seiten c wegnehmen: b + 3d < 3a",
        "Links b weglassen, das wiegt mehr als nichts: 3d < 3a",
        "Durch 3 teilen: d < a. Also ist d leichter als a.",
    ]


def test_balances_can_decide_and_equal_weights_are_allowed() -> None:
    system = scales("b = c", "b + d < a")
    assert heaviest(system) == 0
    assert is_minimal(system)
    for derivation in explain(system):
        assert_valid(derivation)


def test_balance_read_backwards_in_a_derivation() -> None:
    derivation = derive(scales("a = b + c", "d < c"), 3, 0)
    assert_valid(derivation)
    assert derivation.steps()[0] == "Waage 1: b + c = a"


@pytest.mark.parametrize(
    "texts",
    [
        ("b < a", "c < a"),  # d ist frei
        ("b < a", "c < b"),
        ("b + c < a", "a < d"),  # d ist der Schwerste ...
        ("a = b", "c + d < a"),  # a und b gleich schwer
    ],
)
def test_no_unique_heaviest_a(texts: tuple[str, ...]) -> None:
    result = heaviest(scales(*texts))
    if texts == ("b + c < a", "a < d"):
        assert result == 3
    else:
        assert result is None


def test_contradiction_has_no_heaviest() -> None:
    system = scales("b < a", "a < b")
    assert not satisfiable(system)
    assert heaviest(system) is None


def test_one_scale_too_many_is_not_minimal() -> None:
    assert not is_minimal(scales("3d < 2a + c", "b + c + d < a"))
    assert not is_minimal(scales("b < a", "c < a", "d < a", "b + c + d < a"))


def _graph_criterion(system: list[tuple[str, int, int]]) -> int | None:
    """Satz 3 fuer Waagen mit je einem Gegenstand; liefert den Schwersten."""

    parent = list(range(4))

    def find(v: int) -> int:
        while parent[v] != v:
            v = parent[v]
        return v

    for operator, x, y in system:
        if operator == "=":
            parent[find(x)] = find(y)
    classes = {find(v) for v in range(4)}
    edges = {(find(y), find(x)) for operator, x, y in system if operator == "<"}
    # Kreisfreiheit per topologischer Sortierung (Kahn)
    remaining, open_edges = set(classes), set(edges)
    while True:
        sources = [c for c in remaining if not any(b == c for _, b in open_edges)]
        if not sources:
            break
        remaining -= set(sources)
        open_edges = {(a, b) for a, b in open_edges if a not in sources}
    if remaining:
        return None
    for top in range(4):
        if any(find(v) == find(top) for v in range(4) if v != top):
            continue
        reached, frontier = {find(top)}, [find(top)]
        while frontier:
            u = frontier.pop()
            for a, b in edges:
                if a == u and b not in reached:
                    reached.add(b)
                    frontier.append(b)
        if reached == classes:
            return top
    return None


def test_graph_theorem_matches_the_linear_test() -> None:
    rng = random.Random(3)
    for _ in range(300):
        system = [(rng.choice("<="), *rng.sample(range(4), 2)) for _ in range(rng.choice((2, 3, 4)))]
        texts = [f"{'abcd'[x]} {op} {'abcd'[y]}" for op, x, y in system]
        assert heaviest(scales(*texts)) == _graph_criterion(system), texts


# --- Gleichheit ---------------------------------------------------------------


def test_canonical_form_ignores_names_and_order() -> None:
    system = scales("3d < 2a + c", "b + c < a")
    _, key = canonical_form(system)
    rng = random.Random(5)
    for _ in range(10):
        names = list(range(4))
        rng.shuffle(names)
        renamed = [s.renamed(tuple(names)) for s in system]
        rng.shuffle(renamed)
        assert canonical_form(renamed)[1] == key


def test_lower_permutations_fix_a() -> None:
    assert len(LOWER_PERMUTATIONS) == 6
    assert all(p[0] == 0 for p in LOWER_PERMUTATIONS)


# --- Abgleich mit den alten Daten ---------------------------------------------


def test_old_pairs_are_forced_but_96_have_a_superfluous_scale() -> None:
    data = json.loads((ROOT / "data" / "systems-pairs.json").read_text(encoding="utf-8"))["systems"]
    systems = [[Scale.from_mapping(r) for r in s["relations"]] for s in data]
    assert all(heaviest(s) == 0 for s in systems)
    assert sum(is_minimal(s) for s in systems) == 503 - 96


# --- Generator ----------------------------------------------------------------


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_generated_puzzles_are_valid_and_distinct(level: str) -> None:
    settings = LEVELS[level]
    puzzles = list(PuzzleGenerator(settings, seed=11).generate(4))
    keys = set()
    for puzzle in puzzles:
        assert len(puzzle.scales) in settings.scale_counts
        assert all(sum(s.left) <= settings.max_side and sum(s.right) <= settings.max_side for s in puzzle.scales)
        assert all(s.holds(puzzle.weights) for s in puzzle.scales)
        assert heaviest(list(puzzle.scales)) == 0 == puzzle.heaviest
        assert is_minimal(list(puzzle.scales))
        assert settings.min_difficulty <= puzzle.difficulty <= settings.max_difficulty
        for derivation in puzzle.derivations:
            assert_valid(derivation)
        assert canonical_form(list(puzzle.scales))[1] == puzzle.scales
        keys.add(puzzle.scales)
    assert len(keys) == len(puzzles)


def test_generator_is_reproducible() -> None:
    first = [p.scales for p in PuzzleGenerator(LEVELS["mittel"], seed=4).generate(3)]
    second = [p.scales for p in PuzzleGenerator(LEVELS["mittel"], seed=4).generate(3)]
    assert first == second


def test_shuffled_puzzle_keeps_its_meaning() -> None:
    generator = PuzzleGenerator(LEVELS["mittel"], seed=8)
    puzzle = next(generator.generate(1))
    for _ in range(5):
        shuffled = generator.shuffled(puzzle)
        assert all(s.holds(shuffled.weights) for s in shuffled.scales)
        assert heaviest(list(shuffled.scales)) == shuffled.heaviest
        assert shuffled.weights[shuffled.heaviest] == max(shuffled.weights)
        assert canonical_form(list(shuffled.scales))[1] == puzzle.scales


def test_two_single_item_scales_are_rejected() -> None:
    with pytest.raises(ValueError):
        PuzzleGenerator(Settings(scale_counts=(2,), max_side=1))


# --- Kommandozeile ------------------------------------------------------------


def _cli():
    spec = importlib.util.spec_from_file_location("raetsel", ROOT / "raetsel.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cli_writes_json(tmp_path: Path) -> None:
    target = tmp_path / "raetsel.json"
    assert _cli().main(["erzeugen", "--anzahl", "2", "--seed", "1", "--ausgabe", str(target)]) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["metadata"]["count"] == 2
    puzzle = data["puzzles"][0]
    assert puzzle["heaviest"] == "a"
    assert len(puzzle["hints"]) == 3
    assert all(Scale.from_mapping(s).holds([puzzle["example_weights"][n] for n in "abcd"]) for s in puzzle["scales"])


def test_cli_play_round(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter(["h", "x", "a", "q"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    assert _cli().main(["spielen", "--stufe", "leicht", "--seed", "2", "--runden", "1"]) == 0
    output = capsys.readouterr().out
    assert "Hinweis:" in output
    assert "Bitte a, b, c, d, h oder q eingeben." in output
    assert "von 1 Raetseln richtig." in output
