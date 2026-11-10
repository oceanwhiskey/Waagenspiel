"""Vollstaendige, symmetriereduzierte Erzeugung der gesuchten Systeme.

Der optimierte Dreiergenerator arbeitet gegenbeispielgesteuert: Fuer ein
festes Relationspaar wird nicht jede dritte Relation mit einem eigenen
Dominanztest geprueft. Ein einziges Gegenmodell verwirft gleichzeitig alle
Relationen, die in diesem Modell wahr sind. Nur die uebrig bleibenden
Relationen benoetigen einen exakten SMT-Test.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Iterator, Sequence

import z3

from .model import A_FIXED_PERMUTATIONS, NAMES, Relation, System, generate_relations
from .solver import WeightSolver

ProgressCallback = Callable[["GenerationStats"], None]


@dataclass
class GenerationStats:
    relation_count: int = 0
    pair_prefixes: int = 0
    candidates_checked: int = 0
    countermodels: int = 0
    systems_found: int = 0


class SystemGenerator:
    """Erzeugt genau einen Vertreter je Isomorphieklasse mit Maximum ``a``."""

    def __init__(self, solver: WeightSolver | None = None) -> None:
        # Reelle Arithmetik ist hier exakt: Alle Constraints sind homogen und
        # rational; jeder reelle strikte Loesungspunkt kann rational angenaehert
        # und anschliessend zu einer positiven Ganzzahlloesung skaliert werden.
        self.solver = solver or WeightSolver(pairwise_distinct=True, arithmetic="real")
        a, b, c, d = self.solver.variables
        self._a_is_top = z3.And(a > b, a > c, a > d)
        self._a_is_not_top = z3.Or(b >= a, c >= a, d >= a)

        all_relations = sorted(set(generate_relations()), key=lambda relation: relation.key)
        relations: list[Relation] = []
        expressions: list[z3.BoolRef] = []
        for relation in all_relations:
            expression = self.solver.expression(relation)
            check = self.solver._solver((), (self._a_is_top, expression))
            if check.check() == z3.sat:
                relations.append(relation)
                expressions.append(expression)

        self.relations = tuple(relations)
        self.expressions = tuple(expressions)
        self._relation_index = {relation: index for index, relation in enumerate(self.relations)}
        self._permutation_maps = tuple(
            tuple(self._relation_index[relation.renamed(permutation)] for relation in self.relations)
            for permutation in A_FIXED_PERMUTATIONS
        )
        self._orbit_minimum = tuple(
            index
            for index in range(len(self.relations))
            if index == min(mapping[index] for mapping in self._permutation_maps)
        )

    def _is_canonical(self, indices: tuple[int, ...]) -> bool:
        return all(
            indices <= tuple(sorted(mapping[index] for index in indices))
            for mapping in self._permutation_maps
        )

    def _check(self, indices: Sequence[int], extra: z3.BoolRef | None = None) -> z3.CheckSatResult:
        extras = () if extra is None else (extra,)
        solver = self.solver._solver((self.relations[index] for index in indices), extras)
        return solver.check()

    def _pair_can_be_irredundant(self, first: int, second: int) -> bool:
        """Eine paarweise Folgerung macht auch jedes Ober-System redundant."""

        left_countermodel = self.solver._solver(
            (self.relations[first],), (z3.Not(self.expressions[second]),)
        ).check()
        if left_countermodel == z3.unsat:
            return False
        right_countermodel = self.solver._solver(
            (self.relations[second],), (z3.Not(self.expressions[first]),)
        ).check()
        return right_countermodel == z3.sat

    def generate_pairs(self, stats: GenerationStats | None = None) -> Iterator[System]:
        stats = stats or GenerationStats(relation_count=len(self.relations))
        for first in self._orbit_minimum:
            good_solver = self.solver._solver(
                (self.relations[first],), (self._a_is_top,)
            )
            bad_solver = self.solver._solver(
                (self.relations[first],), (self._a_is_not_top,)
            )
            for second in range(first + 1, len(self.relations)):
                indices = (first, second)
                if not self._is_canonical(indices):
                    continue
                stats.candidates_checked += 1
                good_solver.push()
                good_solver.add(self.expressions[second])
                good_result = good_solver.check()
                good_solver.pop()
                if good_result != z3.sat:
                    continue
                bad_solver.push()
                bad_solver.add(self.expressions[second])
                bad_result = bad_solver.check()
                bad_solver.pop()
                if bad_result != z3.unsat:
                    continue
                system = System(self.relations[index] for index in indices)
                if not self.solver.is_irredundant(system):
                    continue
                stats.systems_found += 1
                yield system

    @staticmethod
    def _is_false(model: z3.ModelRef, expression: z3.BoolRef) -> bool:
        return z3.is_false(model.eval(expression, model_completion=True))

    def _satisfiable_extensions(
        self,
        base: z3.Solver,
        candidates: Sequence[int],
        *,
        negate: bool = False,
    ) -> set[int]:
        """Batcht SAT-Tests ``base AND (+/- relation[k])`` ueber Gegenmodelle."""

        if not candidates or base.check() != z3.sat:
            return set()

        def holds(model: z3.ModelRef, index: int) -> bool:
            value = model.eval(self.expressions[index], model_completion=True)
            return z3.is_false(value) if negate else z3.is_true(value)

        model = base.model()
        accepted = {index for index in candidates if holds(model, index)}
        remaining = [index for index in candidates if index not in accepted]
        while remaining:
            candidate = remaining.pop()
            expression = z3.Not(self.expressions[candidate]) if negate else self.expressions[candidate]
            base.push()
            base.add(expression)
            result = base.check()
            if result == z3.unsat:
                base.pop()
                continue
            model = base.model()
            base.pop()
            accepted.add(candidate)
            newly_accepted = {index for index in remaining if holds(model, index)}
            accepted.update(newly_accepted)
            remaining = [index for index in remaining if index not in newly_accepted]
        return accepted

    def _dominance_completions(
        self,
        first: int,
        second: int,
        candidates: list[int],
        stats: GenerationStats,
    ) -> Iterator[int]:
        """Liefert exakt die dritten Relationen, die alle falschen Maxima sperren."""

        base = self.solver._solver(
            (self.relations[first], self.relations[second]),
            (self._a_is_not_top,),
        )
        base_result = base.check()
        if base_result == z3.unsat:
            yield from candidates
            return

        stats.countermodels += 1
        model = base.model()
        remaining = [
            index for index in candidates if self._is_false(model, self.expressions[index])
        ]
        while remaining:
            candidate = remaining.pop()
            base.push()
            base.add(self.expressions[candidate])
            result = base.check()
            if result == z3.unsat:
                base.pop()
                yield candidate
                continue
            stats.countermodels += 1
            model = base.model()
            base.pop()
            remaining = [
                index for index in remaining if self._is_false(model, self.expressions[index])
            ]

    def generate_triples(
        self,
        stats: GenerationStats | None = None,
        *,
        first_indices: Sequence[int] | None = None,
        pair_prefixes: Sequence[tuple[int, int]] | None = None,
        progress: ProgressCallback | None = None,
        progress_every: int = 250,
    ) -> Iterator[System]:
        stats = stats or GenerationStats(relation_count=len(self.relations))
        relation_count = len(self.relations)
        if first_indices is not None and pair_prefixes is not None:
            raise ValueError("first_indices und pair_prefixes duerfen nicht gemeinsam gesetzt werden")
        selected_first_indices = self._orbit_minimum if first_indices is None else tuple(first_indices)
        invalid = set(selected_first_indices) - set(self._orbit_minimum)
        if invalid:
            raise ValueError(f"Ungueltige erste Orbitindizes: {sorted(invalid)}")
        prefixes: Sequence[tuple[int, int]] | Iterator[tuple[int, int]]
        if pair_prefixes is None:
            prefixes = (
                (first, second)
                for first in selected_first_indices
                for second in range(first + 1, relation_count - 1)
            )
        else:
            prefixes = pair_prefixes
        for first, second in prefixes:
                if first not in self._orbit_minimum or not first < second < relation_count - 1:
                    raise ValueError(f"Ungueltiges Paarpraefix: {(first, second)}")
                candidates = [
                    third
                    for third in range(second + 1, relation_count)
                    if self._is_canonical((first, second, third))
                ]
                if not candidates:
                    continue
                stats.pair_prefixes += 1
                if progress is not None and stats.pair_prefixes % progress_every == 0:
                    progress(stats)
                good_solver = self.solver._solver(
                    (self.relations[first], self.relations[second]),
                    (self._a_is_top,),
                )
                if good_solver.check() != z3.sat:
                    continue
                third_is_needed = self.solver._solver(
                    (self.relations[first], self.relations[second])
                )
                second_is_needed = self.solver._solver(
                    (self.relations[first],), (z3.Not(self.expressions[second]),)
                )
                first_is_needed = self.solver._solver(
                    (self.relations[second],), (z3.Not(self.expressions[first]),)
                )
                if second_is_needed.check() != z3.sat or first_is_needed.check() != z3.sat:
                    continue

                completions = list(
                    self._dominance_completions(first, second, candidates, stats)
                )
                stats.candidates_checked += len(completions)
                valid = self._satisfiable_extensions(good_solver, completions)
                valid &= self._satisfiable_extensions(
                    third_is_needed, tuple(valid), negate=True
                )
                valid &= self._satisfiable_extensions(second_is_needed, tuple(valid))
                valid &= self._satisfiable_extensions(first_is_needed, tuple(valid))

                for third in sorted(valid):
                    indices = (first, second, third)
                    system = System(self.relations[index] for index in indices)
                    stats.systems_found += 1
                    yield system

    def generate(
        self,
        *,
        sizes: Sequence[int] = (2, 3),
        stats: GenerationStats | None = None,
        progress: ProgressCallback | None = None,
    ) -> Iterator[System]:
        stats = stats or GenerationStats(relation_count=len(self.relations))
        invalid_sizes = set(sizes) - {2, 3}
        if invalid_sizes:
            raise ValueError(f"Nur Systemgroessen 2 und 3 sind erlaubt: {sorted(invalid_sizes)}")
        if 2 in sizes:
            yield from self.generate_pairs(stats)
        if 3 in sizes:
            yield from self.generate_triples(stats, progress=progress)


def exhaustive_candidates(relations: Sequence[Relation], size: int) -> Iterator[System]:
    """Referenzgenerator ohne Optimierungen, insbesondere fuer kleine Tests."""

    if size not in (2, 3):
        raise ValueError("size muss 2 oder 3 sein")
    for subset in combinations(relations, size):
        yield System(subset)
