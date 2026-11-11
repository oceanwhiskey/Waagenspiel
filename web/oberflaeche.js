// Oberflaeche der Web-Version. Sie zeichnet und nimmt Eingaben an; alles, was das
// Spiel entscheidet, kommt aus einer GameSession (spiel.js), die makeSession liefert.

import {
  DIFFICULTIES,
  GameSession,
  Highscores,
  LEVEL_TITLES,
  RoundSource,
  explain,
  pickCharacters,
  stepsFor,
} from "./spiel.js";
import { ScaleDrawing, animateTilt, character, characterIcon, el } from "./figuren.js";

const $ = (id) => document.getElementById(id);
const SPOTS = [[118, 40], [242, 200], [118, 360]]; // oben links, Mitte rechts, unten links
const TIMES = [30, 60, 90, 120, null];

// localStorage kann fehlen oder gesperrt sein (privater Modus): dann ohne Speichern spielen.
const store = {
  getItem(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  setItem(key, value) {
    try { localStorage.setItem(key, value); } catch { /* egal */ }
  },
};

// --- Ton (ganz leise Pieptoene, abschaltbar) ------------------------------------

class Sound {
  constructor(storage) {
    this.storage = storage;
    this.on = storage?.getItem("waagenspiel.ton") !== "aus";
    this.ctx = null;
  }
  toggle() {
    this.on = !this.on;
    try { this.storage?.setItem("waagenspiel.ton", this.on ? "an" : "aus"); } catch { /* egal */ }
  }
  play(notes) {
    if (!this.on) return;
    try {
      this.ctx ??= new (window.AudioContext || window.webkitAudioContext)();
      let t = this.ctx.currentTime;
      for (const [freq, dur] of notes) {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "triangle";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.12, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
        osc.connect(gain).connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + dur);
        t += dur * 0.8;
      }
    } catch { /* ohne Ton weiterspielen */ }
  }
  right() { this.play([[660, 0.12], [990, 0.18]]); }
  wrong() { this.play([[220, 0.25]]); }
  levelUp() { this.play([[523, 0.1], [659, 0.1], [784, 0.1], [1047, 0.22]]); }
}

// --- Fenster ----------------------------------------------------------------------

class App {
  constructor({ makeSession, highscores, sound }) {
    Object.assign(this, { makeSession, highscores, sound });
    const savedLevel = store.getItem("waagenspiel.stufe");
    this.difficulty = savedLevel in DIFFICULTIES ? savedLevel : "Steigend";
    const savedTime = store.getItem("waagenspiel.zeit");
    const time = savedTime === "ueben" ? null : Number(savedTime);
    this.timeLimit = savedTime !== null && TIMES.includes(time) ? time : 60;
    this.session = null;
    this.round = null;
    this.accepting = false;
    this.timers = new Set();
    this.hintIndex = 0;
    this.preview = pickCharacters(Math.random);
    this.bind();
    this.showStart();
  }

  later(ms, fn) {
    const id = setTimeout(() => { this.timers.delete(id); fn(); }, ms);
    this.timers.add(id);
  }

  clearTimers() {
    this.timers.forEach(clearTimeout);
    this.timers.clear();
    cancelAnimationFrame(this.clockFrame);
  }

  show(id) {
    for (const s of ["start", "spiel", "ende"]) $(s).hidden = s !== id;
    $("blatt").hidden = true;
  }

  bind() {
    $("los").onclick = () => this.startGame();
    $("nochmal").onclick = () => this.startGame();
    $("menue").onclick = () => this.showStart();
    $("zurueck").onclick = () => this.leave();
    $("tipp").onclick = () => this.showHint();
    $("blatt-mehr").onclick = () => this.showHint();
    $("blatt-ok").onclick = () => this.closeSheet();
    $("ton").onclick = () => { this.sound.toggle(); this.updateSoundLabel(); };
    document.addEventListener("keydown", (e) => this.onKey(e));
  }

  onKey(e) {
    const key = e.key.toLowerCase();
    if (key === "escape") return this.leave();
    if (!$("start").hidden && key === "enter") return this.startGame();
    if (!$("ende").hidden && key === "enter") return this.startGame();
    if (["1", "2", "3", "4"].includes(key) && this.accepting) return this.choose(Number(key) - 1);
    if (key === "h" && this.session?.isPractice && this.accepting) return this.showHint();
    if ((key === "enter" || key === " ") && !$("blatt").hidden) {
      e.preventDefault();
      this.closeSheet();
    }
  }

  // --- Start ------------------------------------------------------------------------

  showStart() {
    this.clearTimers();
    this.session = null;
    this.show("start");
    this.chips("wahl-stufe", Object.keys(DIFFICULTIES), (d) => d, this.difficulty, (d) => {
      this.difficulty = d;
      store.setItem("waagenspiel.stufe", d);
    });
    this.chips("wahl-zeit", TIMES, (t) => (t ? `${t} s` : "Üben"), this.timeLimit, (t) => {
      this.timeLimit = t;
      store.setItem("waagenspiel.zeit", t ?? "ueben");
    });
    this.updateRecord();
    this.updateSoundLabel();
    this.drawLogo();
  }

  chips(id, values, label, selected, onSelect) {
    const box = $(id);
    box.replaceChildren();
    for (const value of values) {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.setAttribute("role", "radio");
      chip.setAttribute("aria-checked", String(value === selected));
      chip.textContent = label(value);
      chip.onclick = () => {
        onSelect(value);
        box.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-checked", String(c === chip)));
        this.updateRecord();
      };
      box.appendChild(chip);
    }
  }

  updateRecord() {
    const best = this.highscores.get(Highscores.key(this.difficulty, this.timeLimit));
    $("rekord").textContent = this.timeLimit == null
      ? "Üben: ohne Uhr, mit Tipps und Erklärungen"
      : best ? `Rekord: ${best} Punkte` : "Noch kein Rekord – stell den ersten auf!";
  }

  updateSoundLabel() {
    $("ton").textContent = this.sound.on ? "Ton: an" : "Ton: aus";
  }

  drawLogo() {
    const svg = $("logo");
    svg.replaceChildren();
    const drawing = new ScaleDrawing(svg, 180, 30, { number: 0, left: [0, 1], right: [2, 3, 0], tilt: 0 },
      this.preview, { showNumber: false });
    this.preview.forEach((ch, i) => {
      const fig = character(ch, 22, "happy");
      const [x, y] = [[36, 140], [92, 146], [268, 146], [324, 140]][i];
      fig.setAttribute("transform", `translate(${x},${y})`);
      svg.appendChild(fig);
    });
    const start = performance.now();
    const rock = (now) => {
      if ($("start").hidden) return;
      drawing.set(0.12 * Math.sin((now - start) / 500));
      requestAnimationFrame(rock);
    };
    requestAnimationFrame(rock);
  }

  // --- Spiel --------------------------------------------------------------------------

  startGame() {
    this.clearTimers();
    this.preview = pickCharacters(Math.random);
    this.session = this.makeSession(this.difficulty, this.timeLimit, this.preview);
    this.show("spiel");
    const practice = this.session.isPractice;
    $("tipp").hidden = !practice;
    $("uhr").hidden = practice;
    $("zeitbalken").hidden = practice;
    this.drawCards();
    this.session.start();
    this.showRound();
    if (!practice) this.tick();
  }

  leave() {
    if (this.session && this.session.rounds) this.showEnd();
    else this.showStart();
  }

  updateHeader() {
    const s = this.session;
    $("stand").textContent = `Runde ${s.rounds + 1}  ✔ ${s.correct}  ✘ ${s.wrong}`;
    $("punkte").textContent = `★ ${s.points}`;
    const streak = s.streak >= 2 ? ` · Serie ${s.streak}` : "";
    $("stufe").textContent = `Stufe: ${LEVEL_TITLES[s.difficulty.level]}${streak}`;
  }

  tick() {
    const s = this.session;
    if (!s || s.isPractice) return;
    const left = s.timeLeft();
    const share = left / s.timeLimit;
    $("uhr").textContent = `⏱ ${Math.ceil(left)} s`;
    $("uhr").classList.toggle("knapp", left <= 10);
    const bar = $("zeitbalken").firstElementChild;
    bar.style.width = `${share * 100}%`;
    bar.style.background = left <= 10 ? "var(--bad)" : share < 0.4 ? "var(--gold)" : "var(--good)";
    if (s.isOver()) {
      this.accepting = false;
      this.later(200, () => this.showEnd());
      return;
    }
    this.clockFrame = requestAnimationFrame(() => this.tick());
  }

  drawCards() {
    const box = $("karten");
    box.replaceChildren();
    this.cards = this.session.characters.map((ch, i) => {
      const card = document.createElement("button");
      card.className = "card";
      card.setAttribute("aria-label", ch.name);
      card.append(characterIcon(ch));
      const name = document.createElement("span");
      name.textContent = ch.name;
      const key = document.createElement("span");
      key.className = "key";
      key.textContent = i + 1;
      card.append(name, key);
      card.onclick = () => this.choose(i);
      box.appendChild(card);
      return card;
    });
  }

  resetCards(moodFor = () => "calm") {
    this.cards.forEach((card, i) => {
      card.className = "card";
      card.querySelector("svg").replaceWith(characterIcon(this.session.characters[i], moodFor(i)));
    });
  }

  showRound() {
    const s = this.session;
    this.round = s.current;
    this.updateHeader();
    this.resetCards();
    $("blatt").hidden = true;
    const msg = $("nachricht");
    msg.className = "message";
    msg.textContent = "Welche Figur ist am schwersten?";
    const field = $("feld");
    field.replaceChildren();
    this.drawings = this.round.views.map((view, k) => new ScaleDrawing(field, ...SPOTS[k], view, s.characters));
    this.hintIndex = 0;
    this.accepting = true;
    animateTilt(this.drawings);
  }

  choose(choice) {
    if (!this.accepting || !this.session) return;
    this.accepting = false;
    const feedback = this.session.answer(choice);
    this.updateHeader();
    if (feedback.correct) this.celebrate(choice, feedback);
    else this.reveal(choice, feedback);
  }

  celebrate(choice, feedback) {
    this.resetCards((i) => (i === choice ? "happy" : "calm"));
    this.cards[choice].classList.add("richtig");
    this.drawings.forEach((d) => d.mark(choice, "richtig"));
    let text = `Richtig!  +${feedback.points}`;
    if (feedback.levelAfter > feedback.levelBefore) {
      text += `  Neue Stufe: ${LEVEL_TITLES[feedback.levelAfter]}!`;
      this.sound.levelUp();
    } else {
      if (feedback.streak >= 3) text += `  ${feedback.streak} in Folge!`;
      this.sound.right();
    }
    const msg = $("nachricht");
    msg.className = "message good-text";
    msg.textContent = text;
    this.floatPoints(this.cards[choice], `+${feedback.points}`);
    this.later(750, () => this.nextRound());
  }

  floatPoints(card, text) {
    const rect = card.getBoundingClientRect();
    const node = document.createElement("div");
    node.className = "float";
    node.textContent = text;
    node.style.left = `${rect.left + rect.width / 2}px`;
    node.style.top = `${rect.top - 34}px`;
    document.body.appendChild(node);
    setTimeout(() => node.remove(), 800);
  }

  reveal(choice, feedback) {
    const s = this.session;
    this.resetCards((i) => (i === choice ? "wow" : "calm"));
    this.cards[choice].classList.add("falsch");
    this.cards[feedback.answer].classList.add("loesung");
    this.drawings.forEach((d) => d.mark(feedback.answer, "loesung"));
    this.sound.wrong();
    navigator.vibrate?.(60);
    const right = s.characters[feedback.answer].name;
    const wrong = s.characters[choice].name;
    const msg = $("nachricht");
    msg.className = "message bad-text";
    msg.textContent = `Leider nicht – ${right} ist am schwersten.`;
    if (s.isPractice) {
      const lines = stepsFor(this.round, choice).flatMap((step) => step.text);
      this.openSheet(`Warum ist ${wrong} leichter als ${right}?`, lines, { more: false, ok: "Weiter" });
      this.afterSheet = () => this.nextRound();
    } else {
      this.later(1000, () => this.nextRound());
    }
  }

  showHint() {
    if (!this.accepting || !this.session?.isPractice) return;
    const steps = this.round.steps;
    if (!steps.length) return;
    const index = Math.min(this.hintIndex, steps.length - 1);
    this.hintIndex = index + 1;
    this.openSheet(`Tipp ${index + 1} von ${steps.length}`, steps[index].text, {
      more: this.hintIndex < steps.length,
      ok: "OK",
    });
    this.afterSheet = null;
  }

  openSheet(title, lines, { more, ok }) {
    const s = this.session;
    $("blatt-titel").textContent = title;
    const list = $("blatt-text");
    list.replaceChildren(...lines.map((line) => {
      const li = document.createElement("li");
      li.textContent = explain(line, this.round, s.characters);
      return li;
    }));
    $("blatt-mehr").hidden = !more;
    $("blatt-ok").textContent = ok;
    $("blatt").hidden = false;
    $("blatt").scrollTop = 0;
  }

  closeSheet() {
    $("blatt").hidden = true;
    const next = this.afterSheet;
    this.afterSheet = null;
    next?.();
  }

  nextRound() {
    const s = this.session;
    if (!s) return;
    if (s.isOver()) return this.showEnd();
    s.nextRound();
    this.showRound();
  }

  // --- Ende ---------------------------------------------------------------------------

  showEnd() {
    const s = this.session;
    if (!s) return;
    this.clearTimers();
    const result = s.result();
    const key = Highscores.key(this.difficulty, this.timeLimit);
    const oldBest = this.highscores.get(key);
    const record = !s.isPractice && this.highscores.submit(key, result.points);
    this.session = null;
    this.accepting = false;
    this.show("ende");
    $("ende-titel").textContent = s.isPractice ? "Gut geübt!" : s.isOver() ? "Zeit ist um!" : "Spiel beendet";
    $("ende-rekord").textContent = record ? "★ Neuer Rekord! ★" : oldBest ? `Rekord: ${oldBest} Punkte` : "";
    $("e-runden").textContent = result.rounds;
    $("e-richtig").textContent = result.correct;
    $("e-falsch").textContent = result.wrong;
    $("e-serie").textContent = result.bestStreak;
    $("e-punkte").textContent = result.points;
    const mood = result.correct >= result.wrong ? "happy" : "wow";
    $("ende-figuren").replaceChildren(...this.preview.map((ch) => characterIcon(ch, mood)));
    if (record) this.confetti();
  }

  confetti() {
    const colors = ["#ef476f", "#ffd23f", "#06d6a0", "#3a86ff", "#9b5de5", "#ff8c42"];
    for (let i = 0; i < 70; i++) {
      const piece = document.createElement("div");
      piece.className = "konfetti";
      piece.style.left = `${Math.random() * 100}vw`;
      piece.style.background = colors[i % colors.length];
      piece.style.setProperty("--dx", `${(Math.random() - 0.5) * 120}px`);
      piece.style.animationDuration = `${1.8 + Math.random() * 1.6}s`;
      piece.style.animationDelay = `${Math.random() * 0.6}s`;
      document.body.appendChild(piece);
      setTimeout(() => piece.remove(), 4200);
    }
  }
}

// --- Start ------------------------------------------------------------------------

async function main() {
  const button = $("los");
  button.disabled = true;
  $("laden").textContent = "Rätsel werden geladen …";
  let data;
  try {
    data = await (await fetch("raetsel.json")).json();
  } catch {
    $("laden").textContent = "Die Rätsel konnten nicht geladen werden. Bitte Seite neu laden.";
    return;
  }
  const source = new RoundSource(data.levels);
  const app = new App({
    makeSession: (difficulty, timeLimit, characters) =>
      new GameSession({ source, difficulty: DIFFICULTIES[difficulty](), timeLimit, characters }),
    highscores: new Highscores(store),
    sound: new Sound(store),
  });
  window.waagenspiel = app; // fuer Tests im Browser
  button.disabled = false;
  $("laden").textContent = "";
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}

main();
