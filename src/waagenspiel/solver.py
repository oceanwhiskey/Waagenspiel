"""Exakte SMT-Pruefungen fuer Systeme des Waagenspiels."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import permutations
from typing import TYPE_CHECKING

try:
    import z3
except ModuleNotFoundError as error:  # pragma: no cover - nur hilfreiche Installationsmeldung
    raise ModuleNotFoundError(
        "Das Paket 'z3-solver' fehlt. Installieren mit: pip install -r requirements.txt"
    ) from error

from .model import ALL_PERMUTATIONS, NAMES, Relation, System

if TYPE_CHECKING:
    from z3 import BoolRef, IntNumRef


class WeightSolver:
    """Entscheidet Erfuellbarkeit, Folgerungen und das schwerste Element exakt."""

    def __init__(
        self,
        *,
        pairwise_distinct: bool = True,
        arithmetic: str = "integer",
    ) -> None:
        if arithmetic not in ("integer", "real"):
            raise ValueError("arithmetic muss 'integer' oder 'real' sein")
        constructor = z3.Int if arithmetic == "integer" else z3.Real
        self.variables = tuple(constructor(name) for name in NAMES)
        self.pairwise_distinct = pairwise_distinct
        self.arithmetic = arithmetic
        self.background: tuple[BoolRef, ...] = tuple(variable > 0 for variable in self.variables)
        if pairwise_distinct:
            self.background += (z3.Distinct(*self.variables),)

    def expression(self, relation: Relation) -> BoolRef:
        left = z3.Sum(*(coefficient * variable for coefficient, variable in zip(relation.left, self.variables)))
        right = z3.Sum(*(coefficient * variable for coefficient, variable in zip(relation.right, self.variables)))
        return left == right if relation.operator == "=" else left < right

    def _solver(self, relations: Iterable[Relation] = (), extras: Iterable[BoolRef] = ()) -> z3.Solver:
        solver = z3.Solver()
        solver.add(*self.background)
        solver.add(*(self.expression(relation) for relation in relations))
        solver.add(*extras)
        return solver

    def satisfiable(self, relations: System | Iterable[Relation]) -> bool:
        values = relations.relations if isinstance(relations, System) else relations
        return self._solver(values).check() == z3.sat

    def model(self, relations: System | Iterable[Relation]) -> dict[str, int | str] | None:
        values = relations.relations if isinstance(relations, System) else relations
        solver = self._solver(values)
        if solver.check() != z3.sat:
            return None
        model = solver.model()
        result: dict[str, int | str] = {}
        for name, variable in zip(NAMES, self.variables):
            value = model.eval(variable)
            result[name] = value.as_long() if z3.is_int_value(value) else str(value)
        return result

    def entails_relation(self, premises: Iterable[Relation], conclusion: Relation) -> bool:
        return self._solver(premises, (z3.Not(self.expression(conclusion)),)).check() == z3.unsat

    def entails_heaviest(self, relations: System | Iterable[Relation], name: str) -> bool:
        """Wahr gdw. das System erfuellbar ist und stets ``name`` eindeutig oben liegt."""

        if name not in NAMES:
            raise ValueError(f"Unbekannter Name: {name}")
        values = relations.relations if isinstance(relations, System) else tuple(relations)
        if not self.satisfiable(values):
            return False
        index = NAMES.index(name)
        candidate = self.variables[index]
        counterexample = z3.Or(
            *(other >= candidate for other_index, other in enumerate(self.variables) if other_index != index)
        )
        return self._solver(values, (counterexample,)).check() == z3.unsat

    def possible_heaviest(self, relations: System | Iterable[Relation]) -> frozenset[str]:
        values = relations.relations if isinstance(relations, System) else tuple(relations)
        result: set[str] = set()
        for index, name in enumerate(NAMES):
            candidate = self.variables[index]
            is_top = z3.And(
                *(candidate > other for other_index, other in enumerate(self.variables) if other_index != index)
            )
            if self._solver(values, (is_top,)).check() == z3.sat:
                result.add(name)
        return frozenset(result)

    def unique_heaviest(self, relations: System | Iterable[Relation]) -> str | None:
        possible = self.possible_heaviest(relations)
        return next(iter(possible)) if len(possible) == 1 else None

    def is_irredundant(self, system: System) -> bool:
        for index, relation in enumerate(system.relations):
            remainder = system.relations[:index] + system.relations[index + 1 :]
            if self.entails_relation(remainder, relation):
                return False
        return True

    def semantically_equivalent(
        self,
        left: System,
        right: System,
        *,
        allow_renaming: bool = True,
    ) -> bool:
        """Prueft Gleichheit der Loesungsmengen, optional bis auf Umbenennung."""

        permutations_to_use = ALL_PERMUTATIONS if allow_renaming else ((0, 1, 2, 3),)
        for permutation in permutations_to_use:
            renamed = right.renamed(permutation)
            if all(self.entails_relation(left.relations, relation) for relation in renamed.relations) and all(
                self.entails_relation(renamed.relations, relation) for relation in left.relations
            ):
                return True
        return False
