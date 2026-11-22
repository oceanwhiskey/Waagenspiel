// Spiellogik der Web-Version, ohne jede Oberflaeche (vgl. src/waagenspiel/game.py).
//
// Die Raetsel stammen aus dem exakt gepruefen Katalog (docs/03, Abschnitt 9). Das
// Spiel holt sie vom Server (raetsel.php, alle Raetsel); raetsel.json ist nur der
// Notvorrat ohne Netz. In der kanonischen Form ist immer Gegenstand 0 (a) der
// Schwerste. Fuer jede Runde werden die Gegenstaende umbenannt, die Waagen
// gemischt und manche gespiegelt.

export const COLORS = [
  ["Rot", "#ef476f"],
  ["Blau", "#3a86ff"],
  ["Gelb", "#ffd23f"],
  ["Grün", "#06d6a0"],
  ["Lila", "#9b5de5"],
  ["Orange", "#ff8c42"],
];
export const SHAPES = ["kreis", "quadrat", "dreieck", "tropfen"];
export const LEVEL_TITLES = { 1: "Leicht", 2: "Mittel", 3: "Schwer", 4: "Profi" };
const LETTERS = "abcd";

// --- Zufall --------------------------------------------------------------

export function seededRandom(seed) {
  // mulberry32: klein, schnell, reproduzierbar (fuer Tests)
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffle(items, random) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

// --- Figuren -------------------------------------------------------------

export function pickCharacters(random) {
  const colors = shuffle(COLORS, random).slice(0, 4);
  const shapes = shuffle(SHAPES, random);
  return colors.map(([name, color], i) => ({ name, color, shape: shapes[i] }));
}

// --- Waagen --------------------------------------------------------------

function parseSide(text) {
  const side = [0, 0, 0, 0];
  for (const term of text.split("+")) {
    const match = term.trim().match(/^(\d*)([abcd])$/);
    if (!match) throw new Error(`Unbekannter Term: ${term}`);
    side[LETTERS.indexOf(match[2])] += match[1] ? Number(match[1]) : 1;
  }
  return side;
}

/** "b + 2c < a" -> {left: [0,1,2,0], op: "<", right: [1,0,0,0]}; links ist die leichte Seite. */
export function parseScale(text) {
  const op = text.includes("<") ? "<" : "=";
  const [left, right] = text.split(op);
  return { left: parseSide(left), op, right: parseSide(right) };
}

/** Benennt Gegenstand i in perm[i] um. */
export function renameSide(side, perm) {
  const result = [0, 0, 0, 0];
  side.forEach((count, i) => (result[perm[i]] = count));
  return result;
}

/** Gegenstaende einer Schale; gleiche nebeneinander, ein Paar unten. */
export function panItems(side) {
  const items = [];
  side.forEach((count, i) => {
    for (let k = 0; k < count; k++) items.push(i);
  });
  if (items.length === 3 && items[1] === items[2] && items[2] !== items[0]) return [items[1], items[2], items[0]];
  return items;
}

/** Platz jedes Gegenstands: [waagrechter Versatz in Breiten, Reihe]. */
export function panPositions(count) {
  return { 1: [[0, 0]], 2: [[-0.5, 0], [0.5, 0]], 3: [[-0.5, 0], [0.5, 0], [0, 1]] }[count];
}

/** tilt -1: linke Schale unten (links schwerer), +1: rechte unten, 0: Gleichgewicht. */
export function scaleView(scale, number, mirrored) {
  let left = panItems(scale.left);
  let right = panItems(scale.right);
  let tilt = scale.op === "=" ? 0 : 1;
  if (mirrored) [left, right, tilt] = [right, left, -tilt || 0];
  return { number, left, right, tilt };
}

// --- Runde ----------------------------------------------------------------

/**
 * Macht aus einem Raetsel ({id, s: ["b + c < a", ...]}) eine Runde.
 * perm[i]: neuer Name von Gegenstand i; order[k]: urspruengliche Waage an Platz k.
 */
export function makeRound(puzzle, level, random, mirror = true) {
  const perm = shuffle([0, 1, 2, 3], random);
  const order = shuffle(puzzle.s.map((_, i) => i), random);
  const scales = order.map((i) => {
    const s = parseScale(puzzle.s[i]);
    return { left: renameSide(s.left, perm), op: s.op, right: renameSide(s.right, perm) };
  });
  const views = scales.map((s, k) => scaleView(s, k + 1, mirror && random() < 0.5));
  return { id: puzzle.id, scales, views, answer: perm[0], level, perm, order };
}

// --- Raetselquelle ----------------------------------------------------------

/**
 * Liefert Runden je Stufe. Mit `fetchBatch(level, n)` (Promise einer Liste von
 * Raetseln) haelt sie je Stufe einen kleinen Vorrat vom Server bereit; ist er leer
 * (kein Netz, Server langsam), kommt das Raetsel aus dem Notvorrat `levels`.
 */
export class RoundSource {
  constructor(levels, random = Math.random, fetchBatch = null, clock = () => Date.now()) {
    this.all = levels; // Notvorrat: {"1": [puzzle, ...], ...}
    Object.assign(this, { random, fetchBatch, clock });
    this.pools = {};
    this.queues = {};
    this.loading = {};
    this.pauseUntil = 0; // nach einem Fehler eine Weile nicht nachfragen
  }

  get levels() {
    return Object.keys(this.all).map(Number).sort();
  }

  /** Holt im Hintergrund Raetsel fuer diese Stufen nach. */
  prepare(levels) {
    if (!this.fetchBatch || this.clock() < this.pauseUntil) return;
    for (const level of levels) {
      if (!this.all[level]) continue;
      const queue = (this.queues[level] ??= []);
      if (queue.length >= 5 || this.loading[level]) continue;
      this.loading[level] = this.fetchBatch(level, 20)
        .then((puzzles) => {
          if (!puzzles.length) this.pauseUntil = this.clock() + 60000; // Server hat (noch) keine
          queue.push(...puzzles);
        })
        .catch(() => (this.pauseUntil = this.clock() + 30000))
        .finally(() => (this.loading[level] = null));
    }
  }

  next(level) {
    const queue = this.queues[level];
    const puzzle = queue?.length ? queue.shift() : this.spare(level);
    this.prepare([level - 1, level, level + 1]);
    return makeRound(puzzle, level, this.random);
  }

  spare(level) {
    let pool = this.pools[level];
    if (!pool || !pool.length) pool = this.pools[level] = shuffle(this.all[level], this.random);
    return pool.pop();
  }
}

// --- Schwierigkeit -----------------------------------------------------------

export class FixedDifficulty {
  constructor(level) {
    this.level = level;
  }
  record() {}
}

export class RisingDifficulty {
  constructor(needed = 3) {
    this.level = 1;
    this.needed = needed;
    this.run = 0;
  }
  record(correct) {
    if (correct) {
      this.run += 1;
      if (this.run >= this.needed && this.level < 4) {
        this.level += 1;
        this.run = 0;
      }
    } else {
      this.run = 0;
      this.level = Math.max(1, this.level - 1);
    }
  }
}

export const DIFFICULTIES = {
  Steigend: () => new RisingDifficulty(),
  Leicht: () => new FixedDifficulty(1),
  Mittel: () => new FixedDifficulty(2),
  Schwer: () => new FixedDifficulty(3),
  Profi: () => new FixedDifficulty(4),
};

// --- Partie ------------------------------------------------------------------

// Richtig: Wert des Raetsels (10 je Stufe) mal Serienfaktor (+0,25 je Richtige in
// Folge, hoechstens x3). Falsch: Abzug; sofort geklickt der volle Wert, mit der
// Bedenkzeit gleichmaessig sinkend bis auf ein Drittel (nach 5 s je Stufe). Bei
// einem Drittel bringt blindes Raten unter vier Figuren im Schnitt nichts mehr.
export const SETTLE_SECONDS = 0.75; // so lange pendeln die Waagen ein
export const MAX_FACTOR = 3;

export const valueOf = (level) => 10 * level;
export const thinkSeconds = (level) => 5 * level;

export function streakFactor(streak) {
  return Math.min(1 + 0.25 * (Math.max(streak, 1) - 1), MAX_FACTOR);
}

export function pointsFor(level, streak) {
  return Math.round(valueOf(level) * streakFactor(streak));
}

/** Abzug (positiv) fuer eine falsche Antwort nach `seconds` Bedenkzeit. */
export function penaltyFor(level, seconds) {
  const share = Math.min(1, Math.max(0, seconds) / thinkSeconds(level));
  return Math.round(valueOf(level) * (1 - (2 / 3) * share));
}

/** Eine Partie auf Zeit (timeLimit Sekunden) oder zum Ueben (timeLimit null). */
export class GameSession {
  constructor({ source, difficulty, timeLimit = 60, clock = () => performance.now() / 1000, characters }) {
    Object.assign(this, { source, difficulty, timeLimit, clock, characters });
    this.rounds = this.correct = this.wrong = this.points = this.streak = this.bestStreak = 0;
    this.current = null;
    this.startedAt = null;
    this.shownAt = null;
  }

  get isPractice() {
    return this.timeLimit == null;
  }

  start() {
    this.startedAt = this.clock();
    return this.nextRound();
  }

  nextRound() {
    this.current = this.source.next(this.difficulty.level);
    this.shownAt = this.clock();
    return this.current;
  }

  /** Bedenkzeit der aktuellen Runde, ab dem Einpendeln der Waagen. */
  thinkingTime() {
    return this.shownAt == null ? 0 : Math.max(0, this.clock() - this.shownAt - SETTLE_SECONDS);
  }

  /** Was ein Fehler jetzt kosten wuerde (0 beim Ueben). */
  currentPenalty() {
    if (!this.current || this.isPractice) return 0;
    return penaltyFor(this.current.level, this.thinkingTime());
  }

  /** Serienfaktor, mit dem der naechste Treffer zaehlt. */
  nextFactor() {
    return streakFactor(this.streak + 1);
  }

  /** Was ein Treffer jetzt bringen wuerde (0 beim Ueben). */
  nextPoints() {
    if (!this.current || this.isPractice) return 0;
    return pointsFor(this.current.level, this.streak + 1);
  }

  timeLeft() {
    if (this.isPractice) return null;
    if (this.startedAt == null) return this.timeLimit;
    return Math.max(0, this.timeLimit - (this.clock() - this.startedAt));
  }

  isOver() {
    const left = this.timeLeft();
    return left !== null && left <= 0;
  }

  answer(choice) {
    const round = this.current;
    if (!round) throw new Error("Es laeuft keine Runde");
    const penalty = this.currentPenalty();
    this.current = null;
    const correct = choice === round.answer;
    const levelBefore = this.difficulty.level;
    this.rounds += 1;
    let points;
    if (correct) {
      this.correct += 1;
      this.streak += 1;
      this.bestStreak = Math.max(this.bestStreak, this.streak);
      points = this.isPractice ? 0 : pointsFor(round.level, this.streak);
    } else {
      this.wrong += 1;
      this.streak = 0;
      points = -penalty;
    }
    this.points += points;
    this.difficulty.record(correct);
    return { correct, answer: round.answer, points, streak: this.streak, levelBefore, levelAfter: this.difficulty.level };
  }

  result() {
    const { rounds, correct, wrong, points, bestStreak } = this;
    return { rounds, correct, wrong, points, bestStreak };
  }
}

// --- Bestenliste ----------------------------------------------------------------

export class Highscores {
  // "-v2": seit den Minuspunkten sind alte Rekorde nicht mehr vergleichbar
  constructor(storage, key = "waagenspiel.rekorde-v2") {
    this.storage = storage;
    this.key = key;
    try {
      this.best = JSON.parse(storage?.getItem(key) || "{}") || {};
    } catch {
      this.best = {};
    }
  }

  static key(difficulty, timeLimit) {
    return timeLimit ? `${difficulty}/${timeLimit}s` : `${difficulty}/ueben`;
  }

  get(key) {
    return this.best[key] || 0;
  }

  submit(key, points) {
    if (points <= this.get(key)) return false;
    this.best[key] = points;
    try {
      this.storage?.setItem(this.key, JSON.stringify(this.best));
    } catch {
      /* privater Modus o. ae.: dann eben ohne Speichern */
    }
    return true;
  }
}
