"""Strahlen-Loeser gegen Z3 (docs/03, Abschnitt 11)."""

from __future__ import annotations

import random

import pytest

from waagenspiel.cone import Cone, cone_of, constraints_of
from waagenspiel.puzzle import (
    Scale,
    _fact,
    _side_pairs,
    forces_lighter,
    forces_lighter_z3,
    heaviest,
    satisfiable,
    satisfiable_z3,
)

EVERY = sorted({s for _, _, lt, eq in _side_pairs(3, True) for s in (lt, eq)})
PAIRS = [(x, h) for x in range(4) for h in range(4) if x != h]


def test_orthant_has_four_rays() -> None:
    cone = Cone.orthant()
    assert len(cone.rays) == 4 and cone.satisfiable()
    assert not any(cone.forces_lighter(x, h) for x, h in PAIRS)


def test_example_rays() -> None:
    # b + c < a: Kegel mit Strahlen e_a, e_a + e_b, e_a + e_c, e_d
    cone = cone_of(constraints_of([Scale.parse("b + c < a")]))
    assert set(cone.rays) == {(1, 0, 0, 0), (1, 1, 0, 0), (1, 0, 1, 0), (0, 0, 0, 1)}
    assert cone.forces_lighter(1, 0) and cone.forces_lighter(2, 0)
    assert not cone.forces_lighter(3, 0)


def test_contradiction_and_balance() -> None:
    assert not satisfiable([Scale.parse("b < a"), Scale.parse("a < b")])
    cone = cone_of(constraints_of([Scale.parse("a = b + c")]))
    assert cone.satisfiable() and all(r[0] == r[1] + r[2] for r in cone.rays)


@pytest.mark.parametrize("seed", range(4))
def test_agrees_with_z3_on_random_systems(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(150):
        system = rng.sample(EVERY, rng.choice((1, 2, 3, 4)))
        system += [_fact(*p) for p in rng.sample(PAIRS, rng.choice((0, 0, 1, 2)))]
        assert satisfiable(system) == satisfiable_z3(system), system
        if satisfiable(system):
            x, h = rng.choice(PAIRS)
            assert forces_lighter(system, x, h) == forces_lighter_z3(system, x, h), (system, x, h)


def test_interior_point_is_a_solution() -> None:
    rng = random.Random(9)
    for _ in range(200):
        system = rng.sample(EVERY, rng.choice((1, 2, 3)))
        cone = cone_of(constraints_of(system))
        if cone.satisfiable():
            point = cone.interior_point()
            assert all(v > 0 for v in point) and all(s.holds(point) for s in system)


def test_order_of_constraints_does_not_matter() -> None:
    system = [Scale.parse(t) for t in ("c + 2d < 2a + b", "b + 2d = 3c", "a + b + c = 3d")]
    assert heaviest(system) == heaviest(system[::-1]) == 0
    first = set(cone_of(constraints_of(system)).rays)
    assert first == set(cone_of(constraints_of(system[::-1])).rays)
