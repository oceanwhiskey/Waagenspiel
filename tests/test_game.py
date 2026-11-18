"""Verhalten der Spiellogik (waagenspiel.game), ohne Fenster."""

from __future__ import annotations

import random

import pytest

from waagenspiel.catalog import DEFAULT_PATH
from waagenspiel.game import (
    CatalogRounds,
    FixedDifficulty,
    GameSession,
    Highscores,
    RisingDifficulty,
    Round,
    ScaleView,
    explain_with_names,
    pan_items,
    pan_positions,
    pick_characters,
    SETTLE_SECONDS,
    penalty_for,
    points_for,
    think_seconds,
    round_from_scales,
)
from waagenspiel.puzzle import Scale, forces_heaviest

needs_catalog = pytest.mark.skipif(not DEFAULT_PATH.exists(), reason="data/katalog.json.gz fehlt")

ENTRIES = [
    ["b < a", "c < a", "d < a", 1],
    ["b + c < a", "d < a", 1],
    ["d < c", "c < b", "b < a", 2],
    ["2b < 2a", "c < a", "d < a", 1],  # Vielfache: wird uebersprungen
    ["c + 2d < 2a + b", "b + 2d = 3c", "a + b + c = 3d", 4],
]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class ListSource:
    """Liefert immer dasselbe Raetsel: b < a, c < a, d < a (Antwort a)."""

    def __init__(self) -> None:
        self.levels: list[int] = []

    def next_round(self, level: int) -> Round:
        self.levels.append(level)
        scales = [Scale.parse(t) for t in ("b < a", "c < a", "d < a")]
        return round_from_scales(scales, level, random.Random(0), mirror=False)


# --- Figuren und Waagschalen -----------------------------------------------


def test_characters_differ_in_color_and_shape() -> None:
    for seed in range(20):
        characters = pick_characters(random.Random(seed))
        assert len({c.color for c in characters}) == 4
        assert len({c.shape for c in characters}) == 4


def test_equal_items_lie_next_to_each_other_on_the_ground() -> None:
    assert pan_items((1, 0, 0, 2)) == (3, 3, 0)
    assert pan_items((2, 1, 0, 0)) == (0, 0, 1)
    assert pan_items((0, 1, 1, 1)) == (1, 2, 3)


def test_at_most_two_items_side_by_side_and_third_on_top_in_the_middle() -> None:
    assert pan_positions(1) == ((0.0, 0),)
    assert [row for _, row in pan_positions(2)] == [0, 0]
    assert pan_positions(3)[2] == (0.0, 1)


def test_heavier_pan_hangs_down() -> None:
    scale = Scale.parse("b + c < a")
    view = ScaleView.from_scale(scale, 1, mirrored=False)
    assert view.left == (1, 2) and view.right == (0,) and view.tilt == 1
    mirrored = ScaleView.from_scale(scale, 1, mirrored=True)
    assert mirrored.left == (0,) and mirrored.tilt == -1


def test_balanced_scale_does_not_tilt() -> None:
    assert ScaleView.from_scale(Scale.parse("a = b + c"), 2, mirrored=True).tilt == 0


# --- Runden ---------------------------------------------------------------


def test_renamed_round_keeps_a_unique_heaviest() -> None:
    scales = [Scale.parse(t) for t in ("c + 2d < 2a + b", "b + 2d = 3c", "a + b + c = 3d")]
    for seed in range(10):
        current = round_from_scales(scales, 4, random.Random(seed))
        assert forces_heaviest(list(current.scales), current.answer)
        assert sorted(v.number for v in current.views) == [1, 2, 3]


def test_explanation_says_why_the_choice_is_lighter() -> None:
    current = round_from_scales([Scale.parse(t) for t in ("b < a", "c < b", "d < a")], 2, random.Random(1))
    wrong = next(i for i in range(4) if i != current.answer)
    lines = current.why_lighter(wrong)
    assert lines and "leichter" in lines[-1]


def test_explanations_use_character_names() -> None:
    characters = pick_characters(random.Random(3))
    text = explain_with_names("Zusammen: 2a + b = c + 3d", characters)
    names = [c.name for c in characters]
    assert text == f"Zusammen: 2× {names[0]} + {names[1]} = {names[2]} + 3× {names[3]}"


def test_catalog_rounds_skip_multiples_and_never_repeat() -> None:
    source = CatalogRounds(ENTRIES, random.Random(0), repeat=False)
    seen = {tuple(sorted(map(str, source.next_round(1).scales))) for _ in range(2)}
    assert len(seen) == 2
    with pytest.raises(RuntimeError):
        source.next_round(1)


def test_catalog_rounds_start_over_when_everything_was_played() -> None:
    source = CatalogRounds(ENTRIES, random.Random(0))
    rounds = [source.next_round(2) for _ in range(3)]
    assert all(r.level == 2 for r in rounds)


@needs_catalog
def test_real_catalog_offers_every_level() -> None:
    source = CatalogRounds(rng=random.Random(5))
    assert source.levels == [1, 2, 3, 4]
    for level in source.levels:
        current = source.next_round(level)
        assert current.level == level
        assert forces_heaviest(list(current.scales), current.answer)
        assert all(max(len(v.left), len(v.right)) <= 3 for v in current.views)


# --- Partie -----------------------------------------------------------------


def test_streak_multiplies_the_value_up_to_three_times() -> None:
    assert [points_for(4, n) for n in (1, 2, 3, 5, 9, 20)] == [40, 50, 60, 80, 120, 120]
    session = GameSession(ListSource(), FixedDifficulty(2), clock=FakeClock())
    first = session.start()
    assert session.answer(first.answer).points == 20
    second = session.next_round()
    assert session.answer(second.answer).points == 25
    assert session.result().best_streak == 2


def test_penalty_shrinks_with_thinking_time_to_a_third() -> None:
    assert penalty_for(4, 0) == 40
    assert penalty_for(4, 10) == 27
    assert penalty_for(4, 20) == penalty_for(4, 999) == 13
    assert penalty_for(1, 5) == 3


def test_blind_guessing_never_pays_off() -> None:
    for level in range(1, 5):
        for seconds in (0, 1, think_seconds(level) / 2, think_seconds(level), 100):
            assert 0.25 * points_for(level, 1) - 0.75 * penalty_for(level, seconds) <= 0.5


def test_wrong_answer_costs_points_and_breaks_the_streak() -> None:
    clock = FakeClock()
    session = GameSession(ListSource(), FixedDifficulty(1), clock=clock)
    current = session.start()
    clock.now += SETTLE_SECONDS  # sofort nach dem Einpendeln falsch geklickt
    assert session.current_penalty() == 10
    feedback = session.answer((current.answer + 1) % 4)
    assert not feedback.correct and feedback.answer == current.answer and feedback.streak == 0
    assert feedback.points == -10
    result = session.result()
    assert (result.rounds, result.correct, result.wrong, result.points) == (1, 0, 1, -10)


def test_thinking_longer_makes_a_mistake_cheaper() -> None:
    clock = FakeClock()
    session = GameSession(ListSource(), FixedDifficulty(3), clock=clock)
    current = session.start()
    clock.now += SETTLE_SECONDS + 15
    assert session.answer((current.answer + 1) % 4).points == -10


def test_practice_counts_no_points() -> None:
    session = GameSession(ListSource(), FixedDifficulty(4), time_limit=None, clock=FakeClock())
    current = session.start()
    assert session.answer(current.answer).points == 0
    current = session.next_round()
    assert session.current_penalty() == 0
    assert session.answer((current.answer + 1) % 4).points == 0
    assert session.result().points == 0


def test_game_ends_when_time_is_up() -> None:
    clock = FakeClock()
    session = GameSession(ListSource(), FixedDifficulty(1), time_limit=30, clock=clock)
    session.start()
    clock.now += 29.5
    assert not session.is_over() and session.time_left() == pytest.approx(0.5)
    clock.now += 1
    assert session.is_over() and session.time_left() == 0


def test_practice_never_ends() -> None:
    clock = FakeClock()
    session = GameSession(ListSource(), FixedDifficulty(1), time_limit=None, clock=clock)
    session.start()
    clock.now += 10_000
    assert session.is_practice and not session.is_over() and session.time_left() is None


def test_rising_difficulty_climbs_after_three_in_a_row_and_drops_after_a_mistake() -> None:
    source = ListSource()
    session = GameSession(source, RisingDifficulty(), clock=FakeClock())
    current = session.start()
    for _ in range(3):
        feedback = session.answer(current.answer)
        current = session.next_round()
    assert feedback.level_after == 2 and source.levels[-1] == 2
    feedback = session.answer((current.answer + 1) % 4)
    assert feedback.level_before == 2 and feedback.level_after == 1


def test_rising_difficulty_stops_at_the_top() -> None:
    difficulty = RisingDifficulty(level=4)
    for _ in range(10):
        difficulty.record(True)
    assert difficulty.level == 4


# --- Bestenliste ------------------------------------------------------------


def test_highscores_keep_the_best_and_survive_a_restart(tmp_path) -> None:
    path = tmp_path / "beste.json"
    scores = Highscores(path)
    key = Highscores.key("Mittel", 60)
    assert scores.submit(key, 50)
    assert not scores.submit(key, 40)
    assert Highscores(path).get(key) == 50


def test_broken_highscore_file_is_ignored(tmp_path) -> None:
    path = tmp_path / "beste.json"
    path.write_text("kaputt", encoding="utf-8")
    assert Highscores(path).get("x") == 0


def test_first_hint_is_the_shortcut_when_there_is_one() -> None:
    characters = pick_characters(random.Random(2))
    current = round_from_scales([Scale.parse(t) for t in ("d < c", "c < b", "b < a")], 1, random.Random(4))
    first = [explain_with_names(line, characters) for line in current.hints()[0]]
    assert "nur auf schwereren Seiten" in first[0]
    assert first[-1].endswith(f"{characters[current.answer].name}.")
    assert len(current.hints()) == 1 + len(current.solution.steps)


def test_no_shortcut_hint_when_a_balance_blocks_it() -> None:
    current = round_from_scales([Scale.parse(t) for t in ("d < c", "c < b", "a = 2b")], 2, random.Random(4))
    assert len(current.hints()) == len(current.solution.steps)


def test_next_hit_shows_the_growing_factor() -> None:
    session = GameSession(ListSource(), FixedDifficulty(4), clock=FakeClock())
    current = session.start()
    assert (session.next_factor(), session.next_points()) == (1.0, 40)
    session.answer(current.answer)
    session.next_round()
    assert (session.next_factor(), session.next_points()) == (1.25, 50)
