from __future__ import annotations

from collections import Counter

import pytest

from waagenspiel.model import Relation, System, generate_relations
from waagenspiel.semantic import SemanticCanonicalizer, TheoryCanonicalizer
from waagenspiel.solver import WeightSolver


def relation(left: dict[str, int], operator: str, right: dict[str, int]) -> Relation:
    return Relation.from_mapping(left, operator, right)  # type: ignore[arg-type]


def test_relation_universe_has_the_proved_size() -> None:
    relations = list(generate_relations())
    assert len(relations) == len(set(relations)) == 567
    assert Counter(item.operator for item in relations) == {"<": 378, "=": 189}


def test_relation_normalization_is_primitive_and_directed() -> None:
    assert relation({"a": 2}, "<", {"b": 2}) == relation({"a": 1}, "<", {"b": 1})
    assert relation({"a": 3}, "=", {"b": 3}) == relation({"b": 1}, "=", {"a": 1})
    assert relation({"a": 1}, "<", {"b": 1}) != relation({"b": 1}, "<", {"a": 1})


def test_invalid_relation_is_rejected() -> None:
    with pytest.raises(ValueError):
        relation({"a": 1}, "<", {"a": 1, "b": 1})
    with pytest.raises(ValueError):
        relation({"a": 4}, "<", {"b": 1})


def test_system_equality_is_order_independent_and_renaming_is_canonical() -> None:
    first = relation({"b": 1, "c": 1}, "<", {"a": 1})
    second = relation({"d": 1}, "<", {"a": 1})
    left = System((first, second))
    right = System((second, first))
    renamed = left.renamed((0, 3, 2, 1))
    assert left == right
    assert left.canonical_key(fix_a=True) == renamed.canonical_key(fix_a=True)


@pytest.mark.parametrize("arithmetic", ["integer", "real"])
def test_solver_accepts_valid_pair_and_finds_a(arithmetic: str) -> None:
    system = System(
        (
            relation({"b": 1, "c": 1}, "<", {"a": 1}),
            relation({"d": 1}, "<", {"a": 1}),
        )
    )
    solver = WeightSolver(arithmetic=arithmetic)
    assert solver.satisfiable(system)
    assert solver.unique_heaviest(system) == "a"
    assert solver.is_irredundant(system)


def test_solver_accepts_valid_triple() -> None:
    system = System(
        relation({name: 1}, "<", {"a": 1}) for name in ("b", "c", "d")
    )
    solver = WeightSolver()
    assert solver.unique_heaviest(system) == "a"
    assert solver.is_irredundant(system)


def test_equalities_can_determine_the_heaviest_weight() -> None:
    system = System(
        (
            relation({"a": 1}, "=", {"b": 1, "c": 1}),
            relation({"b": 1}, "=", {"c": 1, "d": 1}),
        )
    )
    assert WeightSolver().unique_heaviest(system) == "a"


def test_redundancy_and_inconsistency_are_detected() -> None:
    redundant = System(
        (
            relation({"b": 1, "c": 1}, "<", {"a": 1}),
            relation({"d": 1}, "<", {"a": 1}),
            relation({"b": 1}, "<", {"a": 1}),
        )
    )
    inconsistent = System(
        (
            relation({"a": 1}, "<", {"b": 1}),
            relation({"b": 1}, "<", {"a": 1}),
        )
    )
    solver = WeightSolver()
    assert not solver.is_irredundant(redundant)
    assert not solver.satisfiable(inconsistent)
    assert solver.unique_heaviest(inconsistent) is None


def test_different_bases_with_the_same_information_are_identified() -> None:
    shared = relation({"a": 1}, "=", {"b": 1, "c": 1})
    left = System((shared, relation({"b": 1}, "=", {"c": 1, "d": 1})))
    right = System((shared, relation({"a": 1}, "=", {"c": 2, "d": 1})))
    assert left.key != right.key
    assert TheoryCanonicalizer.canonical_key(left) == TheoryCanonicalizer.canonical_key(right)

    closure = SemanticCanonicalizer()
    assert closure.canonical_signature(left) == closure.canonical_signature(right)


def test_output_representative_obeys_readme_order_convention() -> None:
    system = System(
        (
            relation({"a": 1}, "=", {"b": 1, "c": 1}),
            relation({"b": 1}, "=", {"c": 1, "d": 1}),
        )
    )
    representative = TheoryCanonicalizer.output_representative(system)
    solver = WeightSolver()
    forbidden = (
        relation({"c": 1}, "<", {"b": 1}),
        relation({"c": 1}, "<", {"d": 1}),
        relation({"b": 1}, "<", {"d": 1}),
    )
    assert all(not solver.entails_relation(representative.relations, item) for item in forbidden)
