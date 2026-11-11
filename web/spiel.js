// Spiellogik der Web-Version, ohne jede Oberflaeche (vgl. src/waagenspiel/game.py).
//
// Die Raetsel stammen aus dem exakt gepruefen Katalog (docs/03, Abschnitt 9) und
// werden von webversion.py samt Loesungsschritten nach raetsel.json exportiert.
// In dieser kanonischen Form ist immer Gegenstand 0 (a) der Schwerste. Fuer jede
// Runde werden die Gegenstaende umbenannt, die Waagen gemischt und manche
// gespiegelt.

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
 * Macht aus einem exportierten Raetsel eine Runde.
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
  const steps = puzzle.steps.map((step) => ({
    fact: [perm[step.f[0]], perm[step.f[1]]],
    requires: step.r.map(([u, v]) => [perm[u], perm[v]]),
    text: step.t,
  }));
  return { scales, views, answer: perm[0], level, perm, order, steps };
}

/** Die Schritte, die zeigen, dass `choice` leichter ist als die Antwort. */
export function stepsFor(round, choice) {
  const key = ([u, v]) => `${u}<${v}`;
  const byFact = new Map(round.steps.map((s) => [key(s.fact), s]));
  const needed = new Set();
  const todo = [[choice, round.answer]];
  while (todo.length) {
    const pair = todo.pop();
    if (needed.has(key(pair)) || !byFact.has(key(pair))) continue;
    needed.add(key(pair));
    todo.push(...byFact.get(key(pair)).requires);
  }
  return round.steps.filter((s) => needed.has(key(s.fact)));
}

/** Ersetzt a-d (auch "2a") durch Figurennamen und "Waage k" durch die gezeigte Nummer. */
export function explain(line, round, characters) {
  return line
    .replace(/\bWaage (\d)\b/g, (_, k) => `Waage ${round.order.indexOf(Number(k) - 1) + 1}`)
    .replace(/\b(\d*)([abcd])\b/g, (_, count, letter) => {
      const name = characters[round.perm[LETTERS.indexOf(letter)]].name;
      return count ? `${count}× ${name}` : name;
    });
}

// --- Raetselquelle ----------------------------------------------------------

export class RoundSource {
  constructor(levels, random = Math.random) {
    this.all = levels; // {"1": [puzzle, ...], ...}
    this.random = random;
    this.pools = {};
  }

  get levels() {
    return Object.keys(this.all).map(Number).sort();
  }

  next(level) {
    let pool = this.pools[level];
    if (!pool || !pool.length) pool = this.pools[level] = shuffle(this.all[level], this.random);
    return makeRound(pool.pop(), level, this.random);
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

export function pointsFor(level, streak) {
  return 10 * level + Math.min(2 * (streak - 1), 20);
}

/** Eine Partie auf Zeit (timeLimit Sekunden) oder zum Ueben (timeLimit null). */
export class GameSession {
  constructor({ source, difficulty, timeLimit = 60, clock = () => performance.now() / 1000, characters }) {
    Object.assign(this, { source, difficulty, timeLimit, clock, characters });
    this.rounds = this.correct = this.wrong = this.points = this.streak = this.bestStreak = 0;
    this.current = null;
    this.startedAt = null;
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
    return this.current;
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
    this.current = null;
    const correct = choice === round.answer;
    const levelBefore = this.difficulty.level;
    this.rounds += 1;
    let points = 0;
    if (correct) {
      this.correct += 1;
      this.streak += 1;
      this.bestStreak = Math.max(this.bestStreak, this.streak);
      points = pointsFor(round.level, this.streak);
      this.points += points;
    } else {
      this.wrong += 1;
      this.streak = 0;
    }
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
  constructor(storage, key = "waagenspiel.bestenliste") {
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
