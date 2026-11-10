"""Vollstaendiger Katalog aller Raetsel (docs/03, Abschnitt 9).

Ein Raetsel ist eine Menge von 2 oder 3 Waagen mit 1 bis 3 Gegenstaenden pro
Seite, in der ``a`` eindeutig echt am schwersten ist und jede Waage gebraucht
wird; gleich sind Raetsel bis auf Umbenennung von b, c, d (Abschnitte 1, 4).

Aufzaehlung:

1. Alle Waagen bilden, die mit ``a`` als Schwerstem vertraeglich sind.
2. Waagen, die ``a`` schon allein bestimmen, fallen weg (nie minimal).
3. Paare und Tripel werden mit vorberechneten Stichproben (alle Gewichte
   1..9 plus unterwegs gefundene Gegenbeispiele) als Bitmasken gefiltert.
   Der Filter verwirft nur Systeme mit echtem Gegenbeispiel; alles andere
   prueft der Strahlen-Loeser exakt. Dadurch geht kein gueltiges Raetsel
   verloren.
4. Fuer jedes Raetsel wird die Stufe aus Abschnitt 8 berechnet.
"""

from __future__ import annotations

import gzip
import json
import multiprocessing as mp
import random
from dataclasses import dataclass
from itertools import product
from math import gcd, lcm
from pathlib import Path
from typing import Callable, Iterator, Sequence

import numpy as np
import z3

from .cone import cone_of, constraints_of
from .puzzle import (
    ALL_PAIRS,
    LOWER_PERMUTATIONS,
    Puzzle,
    Scale,
    Settings,
    _side_pairs,
    level_of,
    solve,
)

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "katalog.json.gz"
SAMPLE_RANGE = 9

Log = Callable[[str], None]


def base_samples() -> np.ndarray:
    return np.array(list(product(range(1, SAMPLE_RANGE + 1), repeat=4)), dtype=np.int64)


# --------------------------------------------------------------------------
# Exakte Einzelpruefungen
# --------------------------------------------------------------------------


def _with(group: Sequence[Scale], extra: Sequence[tuple[tuple[int, int, int, int], str]]):
    return cone_of(tuple(sorted(constraints_of(group) + tuple(extra))))


def _lighter_than_a(x: int, kind: str = "<") -> tuple[tuple[int, int, int, int], str]:
    """Bedingung w_x < w_a (bzw. <=) als (z, Art) mit z = e_x - e_a."""

    z = [0, 0, 0, 0]
    z[x], z[0] = 1, -1
    return tuple(z), kind  # type: ignore[return-value]


def _a_possible(group: Sequence[Scale]) -> bool:
    return _with(group, [_lighter_than_a(x) for x in (1, 2, 3)]).satisfiable()


def _forces_a(group: Sequence[Scale]) -> bool:
    """Erfuellbar und in jeder Loesung ist a echt am schwersten."""

    cone = cone_of(constraints_of(group))
    return cone.satisfiable() and all(cone.forces_lighter(x, 0) for x in (1, 2, 3))


def _counterexample(group: Sequence[Scale]) -> list[int] | None:
    """Ganzzahlige Loesung, in der a nicht echt am schwersten ist."""

    for x in (1, 2, 3):
        z, _ = _lighter_than_a(x)
        cone = _with(group, [(tuple(-v for v in z), "<=")])  # w_a <= w_x
        if cone.satisfiable():
            return list(cone.interior_point())
    return None


# --------------------------------------------------------------------------
# Parallele Arbeiter (auf Modulebene, damit Windows sie starten kann)
# --------------------------------------------------------------------------

_SCALES: list[Scale] = []


def _init_worker(scales: list[Scale]) -> None:
    global _SCALES
    _SCALES = scales


def _check_triple(indices: tuple[int, ...]) -> tuple[int, ...] | None:
    return indices if _forces_a([_SCALES[i] for i in indices]) else None


def _level_task(indices: tuple[int, ...]) -> tuple[tuple[int, ...], int]:
    return indices, level_of([_SCALES[i] for i in indices], top=0)


# --------------------------------------------------------------------------
# Aufzaehlung
# --------------------------------------------------------------------------


def _masks(scales: Sequence[Scale], samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left = np.array([s.left for s in scales], dtype=np.int64) @ samples.T
    right = np.array([s.right for s in scales], dtype=np.int64) @ samples.T
    strict = np.array([s.operator == "<" for s in scales])
    holds = np.where(strict[:, None], left < right, left == right)
    not_a_top = ~(samples[:, 0] > samples[:, 1:].max(axis=1))
    return holds, not_a_top


def build_catalog(workers: int = 4, log: Log = print) -> dict[str, object]:
    """Zaehlt alle Raetsel auf und berechnet ihre Stufen."""

    every = sorted({s for _, _, lt, eq in _side_pairs(3, True) for s in (lt, eq)})
    samples = base_samples()
    holds, not_a_top = _masks(every, samples)
    possible = [
        s for s, ok in zip(every, (holds & ~not_a_top).any(axis=1)) if ok or _a_possible([s])
    ]
    holds, not_a_top = _masks(possible, samples)
    alone = [
        s for s, h in zip(possible, holds) if not (h & not_a_top).any() and _forces_a([s])
    ]
    scales = [s for s in possible if s not in alone]
    n = len(scales)
    log(f"Waagen: {len(every)}, mit a als Schwerstem vertraeglich: {len(possible)}, "
        f"bestimmen a allein: {len(alone)}")

    # Paare
    holds, not_a_top = _masks(scales, samples)
    witnesses: list[list[int]] = []
    pair_forces = np.zeros((n, n), bool)
    pairs: list[tuple[int, int]] = []
    for i in range(n):
        open_ = ~(holds[i + 1 :] & (holds[i] & not_a_top)).any(axis=1)
        for j in (np.nonzero(open_)[0] + i + 1).tolist():
            group = [scales[i], scales[j]]
            if _forces_a(group):
                pair_forces[i, j] = pair_forces[j, i] = True
                pairs.append((i, j))
            else:
                witness = _counterexample(group)
                if witness:
                    witnesses.append(witness)
    log(f"Paare: {len(pairs)} beschriftet, {len(witnesses)} Zusatz-Stichproben")

    position = {s: i for i, s in enumerate(scales)}
    renamings = [np.array([position[s.renamed(p)] for s in scales]) for p in LOWER_PERMUTATIONS]

    def key(indices: tuple[int, ...]) -> tuple[int, ...]:
        return min(tuple(sorted(int(r[i]) for i in indices)) for r in renamings)

    pair_keys = sorted({key(p) for p in pairs})

    # Tripel: Kandidaten ohne Stichproben-Gegenbeispiel, dann Z3
    samples = np.vstack([samples, np.array(witnesses, dtype=np.int64)]) if witnesses else samples
    holds, not_a_top = _masks(scales, samples)
    packed, not_a_top_packed = np.packbits(holds, axis=1), np.packbits(not_a_top)
    candidates: set[tuple[int, ...]] = set()
    for i in range(n):
        for j in range(i + 1, n):
            if pair_forces[i, j]:
                continue
            ks = np.arange(j + 1, n)
            ks = ks[~pair_forces[i, j + 1 :] & ~pair_forces[j, j + 1 :]]
            if not len(ks):
                continue
            open_ = ~(packed[ks] & (packed[i] & packed[j] & not_a_top_packed)).any(axis=1)
            for k in ks[open_].tolist():
                candidates.add(key((i, j, k)))
    log(f"Tripel-Kandidaten: {len(candidates)}")

    with mp.Pool(workers, initializer=_init_worker, initargs=(scales,)) as pool:
        triples = sorted(
            t for t in pool.imap_unordered(_check_triple, sorted(candidates), chunksize=500) if t
        )
    log(f"Raetsel: {len(pair_keys)} mit 2 Waagen, {len(triples)} mit 3 Waagen; berechne Stufen ...")

    levels: dict[tuple[int, ...], int] = {}
    total = len(pair_keys) + len(triples)
    with mp.Pool(workers, initializer=_init_worker, initargs=(scales,)) as pool:
        for done, (indices, level) in enumerate(
            pool.imap_unordered(_level_task, pair_keys + triples, chunksize=200), start=1
        ):
            levels[indices] = level
            if done % 20000 == 0:
                log(f"  Stufen: {done}/{total}")

    puzzles = sorted(
        ([str(scales[i]) for i in t] + [levels[t]] for t in pair_keys + triples),
        key=lambda entry: (len(entry), entry[-1], entry[:-1]),
    )
    counts: dict[str, int] = {}
    for entry in puzzles:
        name = f"{len(entry) - 1}_waagen_stufe_{entry[-1]}"
        counts[name] = counts.get(name, 0) + 1
    return {
        "metadata": {
            "schema_version": 1,
            "source": "docs/03_einfache_herleitung.md, Abschnitt 9",
            "format": "jedes Raetsel: Waagen als Text (a ist der Schwerste), zuletzt die Stufe 1-4",
            "count": len(puzzles),
            "counts": dict(sorted(counts.items())),
        },
        "puzzles": puzzles,
    }


def write_catalog(catalog: dict[str, object], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(catalog, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # Ohne Zeitstempel und Dateinamen im Kopf: gleicher Inhalt, gleiche Datei.
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        handle.write(data)


def load_catalog(path: Path = DEFAULT_PATH) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------
# Raetsel aus dem Katalog ziehen
# --------------------------------------------------------------------------


def example_weights(scales: Sequence[Scale]) -> tuple[int, ...]:
    """Kleinste ganzzahlige Gewichte (nach Summe), die alle Waagen erfuellen."""

    weights = z3.Ints("a b c d")
    opt = z3.Optimize()
    opt.add(*(w >= 1 for w in weights))
    for scale in scales:
        left = sum((k * weights[i] for i, k in enumerate(scale.left) if k), z3.IntVal(0))
        right = sum((k * weights[i] for i, k in enumerate(scale.right) if k), z3.IntVal(0))
        opt.add(left < right if scale.operator == "<" else left == right)
    opt.minimize(sum(weights))
    if opt.check() != z3.sat:
        raise ValueError("Die Waagen sind nicht erfuellbar")
    model = opt.model()
    return tuple(model.eval(w).as_long() for w in weights)


def _matches(scales: Sequence[Scale], level: int, settings: Settings) -> bool:
    return (
        len(scales) in settings.scale_counts
        and all(max(sum(s.left), sum(s.right)) <= settings.max_side for s in scales)
        and settings.min_difficulty <= level <= settings.max_difficulty
        and (settings.allow_multiples or all(gcd(*s.left, *s.right) == 1 for s in scales))
    )


@dataclass
class CatalogSource:
    """Zieht Raetsel ohne Wiederholung aus dem Katalog, gefiltert nach ``settings``."""

    settings: Settings
    seed: int | None = None
    path: Path = DEFAULT_PATH

    def __post_init__(self) -> None:
        entries = load_catalog(self.path)["puzzles"]
        self.pool: list[tuple[tuple[Scale, ...], int]] = []
        for entry in entries:  # type: ignore[union-attr]
            scales = tuple(Scale.parse(text) for text in entry[:-1])
            if _matches(scales, entry[-1], self.settings):
                self.pool.append((scales, entry[-1]))
        self.random = random.Random(self.seed)
        self.random.shuffle(self.pool)

    def __len__(self) -> int:
        return len(self.pool)

    def generate(self, count: int) -> Iterator[Puzzle]:
        if count > len(self.pool):
            raise RuntimeError(f"Der Katalog enthaelt nur noch {len(self.pool)} passende Raetsel")
        for _ in range(count):
            scales, _level = self.pool.pop()
            yield Puzzle(scales, example_weights(scales), solve(scales))

    def shuffled(self, puzzle: Puzzle) -> Puzzle:
        names = list(range(4))
        self.random.shuffle(names)
        order = list(range(len(puzzle.scales)))
        self.random.shuffle(order)
        return puzzle.renamed(tuple(names), order)  # type: ignore[arg-type]
